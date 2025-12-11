from fastapi import APIRouter, UploadFile, File, HTTPException
from fastapi.responses import JSONResponse
import shutil
import os
import uuid
from typing import Optional

router = APIRouter(
    prefix="/files",
    tags=["files"]
)

UPLOAD_DIR = "static/uploads"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

@router.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename)[1]
        unique_filename = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_filename)
        
        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
            
        # Return URL (assuming static mount at /static)
        # In production, this would be an S3 URL or similar
        url = f"/static/uploads/{unique_filename}"
        
        return {"url": url, "filename": unique_filename}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/delete")
async def delete_file(url: str):
    # Basic security check to prevent directory traversal
    if ".." in url:
        raise HTTPException(status_code=400, detail="Invalid file path")
        
    try:
        # Extract filename from URL
        filename = os.path.basename(url)
        file_path = os.path.join(UPLOAD_DIR, filename)
        
        if os.path.exists(file_path):
            os.remove(file_path)
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
