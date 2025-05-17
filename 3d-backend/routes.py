from fastapi import APIRouter, File, UploadFile, HTTPException
import shutil
import os
import json
import uuid
from fastapi.responses import JSONResponse
from .utils.opencv_utils import process_blueprint_image, reconstruct_blueprint, remove_text_from_image
import cv2

router = APIRouter()

UPLOAD_DIR = "uploads/"
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_blueprint(file: UploadFile = File(...)):
    # Generate unique filename to avoid collisions
    unique_id = str(uuid.uuid4())
    filename = f"{unique_id}_{file.filename}"
    file_path = os.path.join(UPLOAD_DIR, filename)

    # Save the uploaded file
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    try:
        # First, remove text from the image
        img_without_text = remove_text_from_image(file_path)
        
        # Save the text-removed image
        text_removed_path = os.path.join(UPLOAD_DIR, f"text_removed_{filename}")
        cv2.imwrite(text_removed_path, img_without_text)
        
        # Process the text-removed blueprint image
        result = process_blueprint_image(text_removed_path)
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Save the processed data as JSON
    json_filename = f"{os.path.splitext(filename)[0]}_blueprint.json"
    json_path = os.path.join(UPLOAD_DIR, json_filename)
    with open(json_path, "w") as json_file:
        json.dump({"data": result}, json_file, indent=2)

    # Reconstruct the blueprint image from the JSON data
    reconstructed_img_path = os.path.join(UPLOAD_DIR, f"reconstructed_{os.path.splitext(filename)[0]}.png")
    reconstruct_blueprint(json_path, output_path=reconstructed_img_path)

    # Return both the reconstructed image and the JSON data
    # We'll encode the image as base64 and include it in the JSON response
    import base64
    with open(reconstructed_img_path, "rb") as img_file:
        encoded_image = base64.b64encode(img_file.read()).decode('utf-8')
    
    # Read the JSON data
    with open(json_path, "r") as json_file:
        blueprint_data = json.load(json_file)
    
    # Return combined response
    response_data = {
        "blueprint_data": blueprint_data,
        "reconstructed_image": encoded_image,
        "image_path": reconstructed_img_path  # Optionally include the path if needed
    }
    
    return JSONResponse(content=response_data)