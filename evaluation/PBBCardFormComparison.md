# OCR Comparison

Ground truth: `test\supplementary-cc-appform.docx`
OCR input: `test/supplementary-cc-appform.pdf`

Text is normalized before comparison to remove DOCX/Markdown formatting wrappers. CER and WER are lower-is-better; all other quality metrics are higher-is-better.

| System | CER | WER | Exact match | Precision | Recall | F1 |
|---|---:|---:|:---:|---:|---:|---:|
| Docling | 0.3768 | 0.4195 | No | 0.6988 | 0.9088 | 0.7900 |
| UnlimitedOCR | 0.9332 | 1.1562 | No | 0.2328 | 0.3283 | 0.2724 |
| DocumentIntelligence | 0.7058 | 0.9066 | No | 0.4275 | 0.2873 | 0.3436 |
| Paddle | 0.4094 | 0.4616 | No | 0.6736 | 0.9228 | 0.7787 |

## Interpretation

- Lower CER/WER means fewer character/word edits against the DOCX reference.
- Precision and recall are sequence-aligned word metrics, so duplicated or reordered OCR text is penalized.
- The JSON also includes order-independent word overlap as a diagnostic for layout/order effects.
- Exact match is intentionally strict and is unlikely for a multi-page form.
