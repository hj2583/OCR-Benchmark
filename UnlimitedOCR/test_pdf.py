import os
import tempfile
import fitz
import torch

from transformers import AutoModel, AutoTokenizer


PDF_PATH = "D:/Git/OCR-Benchmark/test/supplementary-cc-appform.pdf"
OUTPUT_DIR = "output_pdf"


def pdf_to_images(pdf_path, dpi=300):
    doc = fitz.open(pdf_path)

    tmp_dir = tempfile.mkdtemp(prefix="pdf_ocr_")

    paths = []

    matrix = fitz.Matrix(
        dpi / 72,
        dpi / 72
    )

    for i, page in enumerate(doc):

        output = os.path.join(
            tmp_dir,
            f"page_{i + 1:04d}.png"
        )

        page.get_pixmap(
            matrix=matrix
        ).save(output)

        paths.append(output)

    doc.close()

    return paths


print("Loading model...")

tokenizer = AutoTokenizer.from_pretrained(
    "baidu/Unlimited-OCR",
    trust_remote_code=True
)

model = AutoModel.from_pretrained(
    "baidu/Unlimited-OCR",
    trust_remote_code=True,
    use_safetensors=True,
    torch_dtype=torch.bfloat16,
)

model = model.eval().cuda()

print("Converting PDF...")

images = pdf_to_images(
    PDF_PATH,
    dpi=300
)

print(f"Pages: {len(images)}")

print("Running Unlimited-OCR...")

model.infer_multi(
    tokenizer,
    prompt="<image>Multi page parsing.",
    image_files=images,
    output_path=OUTPUT_DIR,
    image_size=1024,
    max_length=32768,
    no_repeat_ngram_size=35,
    ngram_window=1024,
    save_results=True,
)

print("Finished!")