from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import Response
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from io import BytesIO
from PIL import Image
import uvicorn
import os
import logging
import sys

from ai_pipeline import get_transformer
from license_manager import verify_license

from routers import prompt

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)
logger = logging.getLogger(__name__)

app = FastAPI(title="Delulu Clone API", description="An API to apply AI styles to images.")

# Allow CORS for potential frontend integration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure static directory exists
os.makedirs("static", exist_ok=True)

# Mount the static directory to serve the frontend UI
app.mount("/static", StaticFiles(directory="static"), name="static")

# Include Routers
app.include_router(prompt.router, prefix="/api/prompt", tags=["Prompt Generation"])

@app.on_event("startup")
async def startup_event():
    # Verify License
    if not verify_license():
        logger.critical("LICENSE VERIFICATION FAILED!")
        logger.critical("==================================================")
        logger.critical("You have been caught copying this software.")
        logger.critical("This program is strictly bound to its original hardware.")
        logger.critical("Please act genuinely and acquire a valid license.")
        logger.critical("==================================================")
        sys.exit(1)

    # Preload the model on startup so the first request isn't slow
    logger.info("Pre-loading AI model...")
    # Uncomment to actually load on startup (might take memory)
    # get_transformer()
    logger.info("API is ready.")

@app.get("/")
def read_root():
    return {"message": "Welcome to the Delulu Clone API! Visit /static/index.html to use the Web UI."}

@app.post("/api/transform")
async def transform_image(
    file: UploadFile = File(...),
    prompt: str = Form(...),
    strength: float = Form(0.5)
):
    """
    Endpoint to transform an uploaded image using AI.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="File must be an image.")

    try:
        # Read the uploaded image
        image_bytes = await file.read()
        init_image = Image.open(BytesIO(image_bytes))

        # Get the AI transformer
        transformer = get_transformer()

        # Transform the image
        logger.info(f"Transforming image with prompt: '{prompt}', strength: {strength}")
        result_image = transformer.transform_image(init_image, prompt, strength=strength)

        # Save the result to a byte buffer
        output_buffer = BytesIO()
        result_image.save(output_buffer, format="JPEG", quality=90)
        output_buffer.seek(0)

        return Response(content=output_buffer.getvalue(), media_type="image/jpeg")

    except Exception as e:
        logger.error(f"Error transforming image: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8000)
