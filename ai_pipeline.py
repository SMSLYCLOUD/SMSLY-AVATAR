import torch
from diffusers import AutoPipelineForImage2Image
from diffusers.utils import load_image
from PIL import Image

class ImageTransformer:
    def __init__(self):
        # Determine the device to run on
        self.device = "cuda" if torch.cuda.is_available() else "cpu"
        print(f"Loading model on {self.device}...")

        # Using SD-Turbo for fast image-to-image processing.
        # For production with better quality, consider SDXL or SD 1.5,
        # but Turbo is excellent for quick, responsive AI filters.
        model_id = "stabilityai/sd-turbo"

        # Load the pipeline
        self.pipeline = AutoPipelineForImage2Image.from_pretrained(
            model_id,
            torch_dtype=torch.float16 if self.device == "cuda" else torch.float32,
            variant="fp16" if self.device == "cuda" else None
        )
        self.pipeline = self.pipeline.to(self.device)
        print("Model loaded successfully.")

    def transform_image(self, init_image: Image.Image, prompt: str, strength: float = 0.5, num_inference_steps: int = 2) -> Image.Image:
        """
        Transforms the given image based on the prompt.

        :param init_image: The PIL Image to transform.
        :param prompt: The text prompt describing the desired style (e.g., "anime style, masterpiece").
        :param strength: How much to transform the image (0.0 = original, 1.0 = full new image based on prompt).
                         For SD-turbo, 0.5 - 0.7 is a good range.
        :param num_inference_steps: Number of denoising steps. SD-Turbo is designed for 1-4 steps.
        :return: Transformed PIL Image.
        """
        # Ensure image is RGB
        if init_image.mode != "RGB":
            init_image = init_image.convert("RGB")

        # SD models generally expect sizes that are multiples of 8.
        # For SD-Turbo, 512x512 is standard, but we'll try to preserve aspect ratio
        # by resizing while maintaining aspect ratio and ensuring dimensions are multiples of 8.
        # To keep it simple and fast, we resize to max 512 on the longest edge.
        init_image.thumbnail((512, 512), Image.Resampling.LANCZOS)

        width, height = init_image.size
        # Round dimensions to nearest multiple of 8
        width = (width // 8) * 8
        height = (height // 8) * 8
        init_image = init_image.resize((width, height), Image.Resampling.LANCZOS)

        # Enhance the prompt with some quality boosters
        full_prompt = f"{prompt}, highly detailed, best quality, 8k"

        # Generate image
        # Note: guidance_scale is typically 0.0 for SD-Turbo as per model card
        result = self.pipeline(
            prompt=full_prompt,
            image=init_image,
            num_inference_steps=num_inference_steps,
            strength=strength,
            guidance_scale=0.0
        ).images[0]

        return result

# Singleton instance to be imported by the API
# In a real production app, this might be loaded differently to handle multiple workers.
transformer = None

def get_transformer():
    global transformer
    if transformer is None:
        transformer = ImageTransformer()
    return transformer
