import torch
from diffusers import AutoPipelineForImage2Image
import os

print("Pre-downloading stabilityai/sd-turbo model...")
model_id = "stabilityai/sd-turbo"

try:
    pipeline = AutoPipelineForImage2Image.from_pretrained(
        model_id,
        torch_dtype=torch.float16 if torch.cuda.is_available() else torch.float32,
        variant="fp16" if torch.cuda.is_available() else None
    )
    print("Model downloaded and cached successfully.")
except Exception as e:
    print(f"Error downloading model: {e}")
    try:
        print("Retrying without fp16 variant...")
        pipeline = AutoPipelineForImage2Image.from_pretrained(
            model_id,
            torch_dtype=torch.float32
        )
        print("Model downloaded and cached successfully.")
    except Exception as inner_e:
        print(f"Failed to download model completely: {inner_e}")
