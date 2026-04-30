import time
import torch
import logging
import sys
from PIL import Image
import os
import io

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def main():
    logger.info("=========================================")
    logger.info("   SMSLY Avatar - Local Stress Test")
    logger.info("=========================================")
    logger.info("Initializing AI Pipeline...")

    start_load = time.time()
    try:
        from ai_pipeline import get_transformer
        transformer = get_transformer()
    except Exception as e:
        logger.error(f"Failed to load AI pipeline: {e}")
        sys.exit(1)

    load_time = time.time() - start_load

    device = transformer.device
    logger.info(f"Model loaded in {load_time:.2f} seconds.")
    logger.info(f"Active Device: {device.upper()}")

    if device == "cpu":
        logger.warning("\n⚠️ WARNING: You are running on CPU.")
        logger.warning("Real-time video or high-throughput avatar generation is not possible on CPU.")
        logger.warning("Expect ~2-10 seconds PER IMAGE depending on your processor.")
        logger.warning("💡 Recommendation: Use a CUDA-enabled GPU locally, or rent a GPU on vast.ai or RunPod.")
    else:
        logger.info("\n✅ CUDA GPU Detected. Running high-speed inference test.")
        try:
            gpu_name = torch.cuda.get_device_name(0)
            logger.info(f"GPU Model: {gpu_name}")
        except:
            pass

    # Create a dummy image for testing
    img = Image.new('RGB', (512, 512), color='blue')
    prompt = "cyberpunk avatar style, highly detailed, neon lights"

    logger.info("\nWarming up model (1 inference)...")
    try:
        # Note SD-Turbo requires strength < 1.0. and guidance scale = 0.0 is passed in our pipeline
        transformer.transform_image(img, prompt, strength=0.6, num_inference_steps=2)
    except Exception as e:
        logger.error(f"Warmup failed: {e}")
        sys.exit(1)

    num_iterations = 10 if device == "cuda" else 3
    logger.info(f"\nRunning {num_iterations} consecutive generations...")

    total_time = 0

    # We clear the cache to ensure we're testing raw inference speed, not our caching layer
    transformer.cache.clear()

    for i in range(num_iterations):
        # Slightly change prompt to bypass cache
        iter_prompt = f"{prompt}, iteration {i}"

        start_time = time.time()
        transformer.transform_image(img, iter_prompt, strength=0.6, num_inference_steps=2)
        end_time = time.time()

        iteration_time = end_time - start_time
        total_time += iteration_time

        logger.info(f"  [{i+1}/{num_iterations}] Generated in {iteration_time:.3f}s")

    avg_time = total_time / num_iterations
    fps = 1.0 / avg_time if avg_time > 0 else 0

    logger.info("\n=========================================")
    logger.info("   STRESS TEST RESULTS")
    logger.info("=========================================")
    logger.info(f"Average time per image: {avg_time:.3f} seconds")
    logger.info(f"Estimated Throughput:   {fps:.2f} frames per second (FPS)")

    if device == "cpu":
        logger.info("\nConclusion: CPU performance is functioning normally for static generation.")
        logger.info("If you want live video, please use a GPU instance (e.g. vast.ai RTX 3090/4090).")
    elif fps < 5:
        logger.info("\nConclusion: Your GPU is working but may be underpowered for smooth real-time video.")
        logger.info("Real-time video typically requires 15+ FPS.")
        logger.info("Try optimizing with TensorRT, reducing resolution, or upgrading your GPU (vast.ai).")
    else:
        logger.info("\nConclusion: Excellent GPU performance! You have enough throughput to build a live video pipeline.")
        logger.info("Note: True real-time video requires implementing a dedicated streaming loop (WebRTC/WebSocket) rather than REST API calls.")

if __name__ == "__main__":
    # Disable some noisy diffusers logs
    logging.getLogger("diffusers").setLevel(logging.ERROR)
    main()
