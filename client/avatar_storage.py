import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException
from PIL import Image
from io import BytesIO

UPLOAD_DIR = os.environ.get("SMSLY_AVATAR_UPLOAD_DIR", "./data/avatar_uploads")
MAX_UPLOAD_MB = int(os.environ.get("SMSLY_AVATAR_MAX_UPLOAD_MB", "10"))
MAX_UPLOAD_BYTES = MAX_UPLOAD_MB * 1024 * 1024

ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/png", "image/webp", "image/jpg"}

async def save_avatar_upload(file: UploadFile) -> tuple[str, str]:
    if file.content_type not in ALLOWED_CONTENT_TYPES:
        raise HTTPException(status_code=400, detail=f"Unsupported file type: {file.content_type}")

    # Read the file content
    contents = await file.read()

    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail=f"File exceeds max upload size of {MAX_UPLOAD_MB}MB.")

    # Validate image using PIL
    try:
        image = Image.open(BytesIO(contents))
        image.verify() # Verify that it is, in fact, an image
    except Exception as e:
        raise HTTPException(status_code=400, detail="Invalid image file.")

    # Generate unique filename
    ext = file.filename.split(".")[-1].lower() if "." in file.filename else "jpg"
    unique_filename = f"{uuid.uuid4().hex}.{ext}"

    # Paths
    skin_dir = os.path.join(UPLOAD_DIR, "skins")
    os.makedirs(skin_dir, exist_ok=True)
    file_path = os.path.join(skin_dir, unique_filename)

    # Save file
    with open(file_path, "wb") as f:
        f.write(contents)

    url = f"/avatar-media/skins/{unique_filename}"
    return file_path, url
