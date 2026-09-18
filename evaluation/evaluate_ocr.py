"""Compare OCR Markdown outputs with the source DOCX text."""

from __future__ import annotations

import argparse
from collections import Counter
import difflib
import html
import json
import re
import zipfile
from pathlib import Path
from xml.etree import ElementTree

try:
    from rapidfuzz.distance import Levenshtein
except ImportError:  # Keep the evaluator usable before optional dependencies are installed.
    Levenshtein = None


WORD_PATTERN = re.compile(r"\b[\w']+\b", re.UNICODE)
TAG_PATTERN = re.compile(r"<[^>]+>")
IMAGE_PATTERN = re.compile(r"!\[[^\]]*\]\([^)]*\)")
DOCX_NS = "http://schemas.openxmlformats.org/wordprocessingml/2006/main"


def extract_docx_text(path: Path) -> str:
    """Extract paragraphs and tables in document order from a DOCX file."""
    with zipfile.ZipFile(path) as archive:
        root = ElementTree.fromstring(archive.read("word/document.xml"))

    lines: list[str] = []
    body = root.find(f"{{{DOCX_NS}}}body")
    if body is None:
        return ""
    for child in body:
        if child.tag == f"{{{DOCX_NS}}}p":
            value = "".join(node.text or "" for node in child.iter(f"{{{DOCX_NS}}}t"))
            if value.strip():
                lines.append(value)
        elif child.tag == f"{{{DOCX_NS}}}tbl":
            for row in child.findall(f"{{{DOCX_NS}}}tr"):
                cells = []
                for cell in row.findall(f"{{{DOCX_NS}}}tc"):
                    cells.append(" ".join(
                        "".join(node.text or "" for node in paragraph.iter(f"{{{DOCX_NS}}}t"))
                        for paragraph in cell.findall(f".//{{{DOCX_NS}}}p")
                    ).strip())
                line = " | ".join(cell for cell in cells if cell)
                if line:
                    lines.append(line)
    return "\n".join(lines)


def normalize_text(value: str) -> str:
    """Remove representation-only markup while preserving OCR characters."""
    value = html.unescape(value).replace("\u00a0", " ")
    value = IMAGE_PATTERN.sub("", value)
    value = re.sub(r"^\s*\[Non-Text\]\s*$", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*<PAGE>\s*$", "", value, flags=re.MULTILINE)
    value = TAG_PATTERN.sub(" ", value)
    value = re.sub(r"^\s{0,3}#{1,6}\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*[-*+]\s+\[\s*[xX ]?\s*\]\s*", "", value, flags=re.MULTILINE)
    value = re.sub(r"^\s*[-*+]\s+", "", value, flags=re.MULTILINE)
    value = re.sub(r"\s+", " ", value)
    return value.strip().casefold()


def matching_units(reference: list[str], candidate: list[str]) -> int:
    matcher = difflib.SequenceMatcher(None, reference, candidate, autojunk=False)
    return sum(block.size for block in matcher.get_matching_blocks())


def exact_distance(reference: list[str], candidate: list[str]) -> int:
    if Levenshtein is not None:
        return Levenshtein.distance(reference, candidate)
    previous = list(range(len(candidate) + 1))
    for row, reference_unit in enumerate(reference, 1):
        current = [row]
        for column, candidate_unit in enumerate(candidate, 1):
            current.append(min(
                current[-1] + 1,
                previous[column] + 1,
                previous[column - 1] + (reference_unit != candidate_unit),
            ))
        previous = current
    return previous[-1]


def score(reference: str, candidate: str) -> dict[str, float | int | bool]:
    reference_words = WORD_PATTERN.findall(reference)
    candidate_words = WORD_PATTERN.findall(candidate)
    reference_chars = list(reference)
    candidate_chars = list(candidate)
    char_matches = matching_units(reference_chars, candidate_chars)
    word_matches = matching_units(reference_words, candidate_words)
    char_precision = char_matches / len(candidate_chars) if candidate_chars else 0.0
    char_recall = char_matches / len(reference_chars) if reference_chars else 0.0
    word_precision = word_matches / len(candidate_words) if candidate_words else 0.0
    word_recall = word_matches / len(reference_words) if reference_words else 0.0
    overlap_matches = sum((Counter(reference_words) & Counter(candidate_words)).values())

    def f1(precision: float, recall: float) -> float:
        return 2 * precision * recall / (precision + recall) if precision + recall else 0.0

    return {
        "reference_characters": len(reference_chars),
        "candidate_characters": len(candidate_chars),
        "reference_words": len(reference_words),
        "candidate_words": len(candidate_words),
        "cer": exact_distance(reference_chars, candidate_chars) / len(reference_chars) if reference_chars else 0.0,
        "wer": exact_distance(reference_words, candidate_words) / len(reference_words) if reference_words else 0.0,
        "exact_match": reference == candidate,
        "precision": word_precision,
        "recall": word_recall,
        "f1": f1(word_precision, word_recall),
        "order_independent_precision": overlap_matches / len(candidate_words) if candidate_words else 0.0,
        "order_independent_recall": overlap_matches / len(reference_words) if reference_words else 0.0,
        "character_precision": char_precision,
        "character_recall": char_recall,
        "character_f1": f1(char_precision, char_recall),
    }


def load_text(path: Path) -> str:
    return extract_docx_text(path) if path.suffix.lower() == ".docx" else path.read_text(encoding="utf-8", errors="replace")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, default=Path(__file__).parents[1])
    parser.add_argument("--output", type=Path, default=None)
    args = parser.parse_args()
    root = args.root.resolve()
    ground_truth_path = root / "test" / "supplementary-cc-appform.docx"
    sources = {
        "Docling": root / "docling-test" / "supplementary-cc-appform.md",
        "UnlimitedOCR": root / "UnlimitedOCR" / "PBBCardForm" / "result.md",
        "DocumentIntelligence": root / "AzureDocumentInt" / "supplementary-cc-appform.md",
        "Paddle": root / "Paddle" / "PaddleResult" / "opensource_table_extraction_summary_readable.md",
    }
    reference = normalize_text(load_text(ground_truth_path))
    results = {}
    for name, path in sources.items():
        raw = load_text(path)
        results[name] = score(reference, normalize_text(raw))
        results[name]["source"] = str(path.relative_to(root))

    report = {
        "ground_truth": str(ground_truth_path.relative_to(root)),
        "ocr_input": "test/supplementary-cc-appform.pdf",
        "normalization": "casefolded text with DOCX/Markdown representation markup removed",
        "results": results,
    }
    output = args.output or root / "evaluation" / "results.json"
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(report, indent=2), encoding="utf-8")

    lines = [
        "# OCR Comparison",
        "",
        f"Ground truth: `{report['ground_truth']}`",
        "OCR input: `test/supplementary-cc-appform.pdf`",
        "",
        "Text is normalized before comparison to remove DOCX/Markdown formatting wrappers. CER and WER are lower-is-better; all other quality metrics are higher-is-better.",
        "",
        "| System | CER | WER | Exact match | Precision | Recall | F1 |",
        "|---|---:|---:|:---:|---:|---:|---:|",
    ]
    for name, values in results.items():
        lines.append(f"| {name} | {values['cer']:.4f} | {values['wer']:.4f} | {'Yes' if values['exact_match'] else 'No'} | {values['precision']:.4f} | {values['recall']:.4f} | {values['f1']:.4f} |")
    lines += [
        "",
        "## Interpretation",
        "",
        "- Lower CER/WER means fewer character/word edits against the DOCX reference.",
        "- Precision and recall are sequence-aligned word metrics, so duplicated or reordered OCR text is penalized.",
        "- The JSON also includes order-independent word overlap as a diagnostic for layout/order effects.",
        "- Exact match is intentionally strict and is unlikely for a multi-page form.",
    ]
    (output.parent / "comparison.md").write_text("\n".join(lines) + "\n", encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()