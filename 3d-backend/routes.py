

from fastapi import APIRouter, File, UploadFile
import shutil
import os

router = APIRouter()

UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_blueprint(file: UploadFile = File(...)):
    file_path = os.path.join(UPLOAD_DIR, file.filename)

    # Save the file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Optionally process the file here (e.g., run CV logic)
    return {"filename": file.filename, "message": "File uploaded successfully"}
