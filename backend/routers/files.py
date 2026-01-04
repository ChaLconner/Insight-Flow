"""
File upload router with security hardening.
Implements: extension whitelist, MIME validation, size limits, path traversal protection.

Security features are centralized in utils/file_security.py
"""

import os
import uuid

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from models.file import File as FileModel
from models.user import User
from routers.auth import get_current_active_user
from utils.file_security import (
    FileSecurityError,
    validate_file_path,
    validate_general_upload,
)
from utils.logger import mask_user_id, setup_logger

logger = setup_logger("files_router")

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = "static/uploads"

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Upload a file with security validation.

    Security measures:
    - File extension whitelist
    - MIME type validation (must match extension)
    - File size limit (10 MB)
    - Path traversal protection
    - UUID-based filenames to prevent collisions
    """
    try:
        # Read file content
        content = await file.read()

        # Security: Validate file upload (extension, MIME type, size)
        try:
            file_extension, file_size = validate_general_upload(
                filename=file.filename,
                content_type=file.content_type,
                content=content,
            )
        except FileSecurityError as e:
            logger.warning(
                f"File upload security violation by user {mask_user_id(str(current_user.id))}: {e.message}"
            )
            raise HTTPException(status_code=400, detail=e.message)

        # Generate unique filename with validated extension
        unique_name = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # Validate the final path to prevent directory traversal
        try:
            validated_path = validate_file_path(UPLOAD_DIR, file_path)
        except FileSecurityError:
            logger.warning(f"Path traversal attempt by user {mask_user_id(str(current_user.id))}")
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Save file
        with open(validated_path, "wb") as buffer:
            buffer.write(content)

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

        logger.info(f"File uploaded by user {mask_user_id(str(current_user.id))}: {unique_name}")
        return {"url": url, "filename": unique_name, "id": str(db_file.id)}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


@router.delete("/delete")
async def delete_file(
    url: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Delete a file with security validation.

    Security measures:
    - Path traversal protection
    - Ownership verification (only file owner can delete)
    - Filename sanitization
    """
    try:
        # Security: Check for path traversal in the input URL immediately
        if ".." in url:
            logger.warning(
                f"Path traversal attempt by user {mask_user_id(str(current_user.id))}: {url[:50]}"
            )
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Extract filename from URL (only basename, strips any path components)
        filename = os.path.basename(url)

        # Validate filename doesn't contain suspicious patterns
        if not filename or ".." in filename or "/" in filename or "\\" in filename:
            logger.warning(
                f"Suspicious delete attempt by user {mask_user_id(str(current_user.id))}: {url[:50]}"
            )
            raise HTTPException(status_code=400, detail="Invalid file path")

        file_path = os.path.join(UPLOAD_DIR, filename)

        # Validate the final path is within upload directory
        try:
            validated_path = validate_file_path(UPLOAD_DIR, file_path)
        except FileSecurityError:
            raise HTTPException(status_code=400, detail="Invalid file path")

        # Check ownership in database
        from sqlalchemy import select

        result = await db.execute(select(FileModel).where(FileModel.unique_filename == filename))
        db_file = result.scalar_one_or_none()

        if db_file:
            # Security: Check ownership before deletion
            if db_file.user_id != current_user.id:
                logger.warning(
                    f"Unauthorized delete attempt by user {mask_user_id(str(current_user.id))} "
                    f"on file owned by {mask_user_id(str(db_file.user_id))}"
                )
                raise HTTPException(status_code=403, detail="Not authorized to delete this file")

            await db.delete(db_file)
            await db.commit()

        if os.path.exists(validated_path):
            os.remove(validated_path)
            logger.info(f"File deleted by user {mask_user_id(str(current_user.id))}: {filename}")
            return {"message": "File deleted successfully"}
        else:
            raise HTTPException(status_code=404, detail="File not found")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail="File deletion failed")
