import os
import shutil
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile

from models.user import User
from routers.auth import get_current_active_user
from utils.logger import mask_user_id, setup_logger

logger = setup_logger("files_router")

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "static/uploads"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)

from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from models.file import File as FileModel


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    try:
        # Generate unique filename
        file_extension = os.path.splitext(file.filename or "")[1]
        unique_name = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # Save file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Get file size
        file_size = os.path.getsize(file_path)

        # Return URL (assuming static mount at /static)
        url = f"/static/uploads/{unique_name}"

        # Save to DB
        db_file = FileModel(
            user_id=current_user.id,
            filename=file.filename,
            unique_filename=unique_name,
            url=url,
            size_bytes=file_size,
            mime_type=file.content_type,
        )
        db.add(db_file)
        await db.commit()

        logger.info(f"File uploaded by user {mask_user_id(current_user.id)}: {unique_name}")
        return {"url": url, "filename": unique_name, "id": str(db_file.id)}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/delete")
async def delete_file(
    url: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    # Basic security check to prevent directory traversal
    if ".." in url:
        raise HTTPException(status_code=400, detail="Invalid file path")

    try:
        # Extract filename from URL
        filename = os.path.basename(url)
        file_path = os.path.join(UPLOAD_DIR, filename)

        # Delete from DB
        from sqlalchemy import select

        result = await db.execute(select(FileModel).where(FileModel.unique_filename == filename))
        db_file = result.scalar_one_or_none()

        if db_file:
            # Check ownership? Strictly speaking yes, but filename is UUID so maybe fine.
            # But let's check ownership for security.
            if db_file.user_id != current_user.id:
                raise HTTPException(status_code=403, detail="Not authorized to delete this file")

            await db.delete(db_file)
            await db.commit()

        if os.path.exists(file_path):
            os.remove(file_path)
            logger.info(f"File deleted by user {mask_user_id(current_user.id)}: {filename}")
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
