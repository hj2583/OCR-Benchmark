import torch
from transformers import AutoModel, AutoTokenizer

model_name = "baidu/Unlimited-OCR"

print("Loading tokenizer...")
tokenizer = AutoTokenizer.from_pretrained(
    model_name,
    trust_remote_code=True
)

print("Loading model...")
model = AutoModel.from_pretrained(
    model_name,
    trust_remote_code=True,
    use_safetensors=True,
    torch_dtype=torch.bfloat16,
)

model = model.eval().cuda()

print("Running OCR...")

model.infer(
    tokenizer,
    prompt="<image>document parsing.",
    image_file="D:/Git/OCR-Benchmark/test/contract.png",
    output_path="output",
    base_size=1024,
    image_size=640,
    crop_mode=True,
    max_length=32768,
    no_repeat_ngram_size=35,
    ngram_window=128,
    save_results=True,
)

print("Done!")