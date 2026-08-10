"""
File upload router with security hardening.
Implements: extension whitelist, MIME validation, size limits, path traversal protection.

Security features are centralized in utils/file_security.py
"""

import asyncio
import os
import uuid
from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from fastapi.responses import FileResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_async_db
from models.file import File as FileModel
from models.user import User
from routers.auth import get_current_active_user
from utils.file_security import (
    MAX_FILE_SIZE_BYTES,
    FileSecurityError,
    read_upload_with_limit,
    validate_file_path,
    validate_general_upload,
)
from utils.logger import mask_user_id, setup_logger

logger = setup_logger("files_router")

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = str(Path(__file__).resolve().parent.parent / "storage" / "private_uploads")
DOWNLOAD_URL_PREFIX = "/api/v1/files/download"

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
    validated_path: str | None = None
    file_committed = False
    try:
        # Read in bounded chunks so the request body cannot exhaust process memory.
        try:
            content = await read_upload_with_limit(file, MAX_FILE_SIZE_BYTES)
        except FileSecurityError as e:
            logger.warning(
                f"File upload security violation by user {mask_user_id(str(current_user.id))}: {e.message}"
            )
            raise HTTPException(status_code=400, detail=e.message)

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
        await asyncio.to_thread(_write_binary_file, validated_path, content)

        url = f"{DOWNLOAD_URL_PREFIX}/{unique_name}"

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
        file_committed = True

        logger.info(f"File uploaded by user {mask_user_id(str(current_user.id))}: {unique_name}")
        return {"url": url, "filename": unique_name, "id": str(db_file.id)}

    except HTTPException:
        if not file_committed and validated_path and os.path.exists(validated_path):
            try:
                os.remove(validated_path)
            except OSError as cleanup_error:
                logger.warning(f"Failed to remove rejected upload: {cleanup_error}")
        raise
    except Exception as e:
        await db.rollback()
        if not file_committed and validated_path and os.path.exists(validated_path):
            try:
                os.remove(validated_path)
            except OSError as cleanup_error:
                logger.warning(f"Failed to remove incomplete upload: {cleanup_error}")
        logger.error(f"File upload error: {e}")
        raise HTTPException(status_code=500, detail="File upload failed")


def _write_binary_file(path: str, content: bytes) -> None:
    """Write upload bytes off the event loop."""
    with open(path, "wb") as buffer:
        buffer.write(content)


def _resolve_upload_path(url: str, current_user: User) -> tuple[str, str]:
    if ".." in url:
        logger.warning(
            f"Path traversal attempt by user {mask_user_id(str(current_user.id))}: {url[:50]}"
        )
        raise HTTPException(status_code=400, detail="Invalid file path")

    filename = os.path.basename(url)
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(
            f"Suspicious file path by user {mask_user_id(str(current_user.id))}: {url[:50]}"
        )
        raise HTTPException(status_code=400, detail="Invalid file path")

    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        validated_path = validate_file_path(UPLOAD_DIR, file_path)
    except FileSecurityError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    return filename, validated_path


@router.get("/info")
async def get_file_info(
    url: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """
    Return metadata for an uploaded file.

    Mirrors the frontend fileApi.getFileInfo contract and enforces the same
    traversal and ownership checks as deletion.
    """
    try:
        filename, validated_path = _resolve_upload_path(url, current_user)

        result = await db.execute(select(FileModel).where(FileModel.unique_filename == filename))
        db_file = result.scalar_one_or_none()

        if db_file and db_file.user_id != current_user.id:
            logger.warning(
                f"Unauthorized file info attempt by user {mask_user_id(str(current_user.id))} "
                f"on file owned by {mask_user_id(str(db_file.user_id))}"
            )
            raise HTTPException(status_code=403, detail="Not authorized to access this file")

        exists = os.path.exists(validated_path)
        if not db_file:
            # Do not expose or delete orphaned files by filename. A separate
            # operator reconciliation job can remove rows/files safely.
            raise HTTPException(status_code=404, detail="File not found")

        return {
            "url": db_file.url if db_file else f"{DOWNLOAD_URL_PREFIX}/{filename}",
            "filename": db_file.filename if db_file else filename,
            "unique_filename": db_file.unique_filename if db_file else filename,
            "size_bytes": db_file.size_bytes if db_file else os.path.getsize(validated_path),
            "mime_type": db_file.mime_type if db_file else None,
            "exists": exists,
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File info error: {e}")
        raise HTTPException(status_code=500, detail="File info lookup failed")


@router.get("/download/{filename}")
async def download_file(
    filename: str,
    current_user: User = Depends(get_current_active_user),
    db: AsyncSession = Depends(get_async_db),
):
    """Download an uploaded file after ownership verification."""
    try:
        resolved_filename, validated_path = _resolve_upload_path(filename, current_user)
        result = await db.execute(
            select(FileModel).where(FileModel.unique_filename == resolved_filename)
        )
        db_file = result.scalar_one_or_none()

        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")
        if db_file.user_id != current_user.id:
            logger.warning(
                f"Unauthorized file download attempt by user {mask_user_id(str(current_user.id))} "
                f"on file owned by {mask_user_id(str(db_file.user_id))}"
            )
            raise HTTPException(status_code=403, detail="Not authorized to access this file")
        if not os.path.exists(validated_path):
            raise HTTPException(status_code=404, detail="File not found")

        return FileResponse(
            validated_path,
            media_type=db_file.mime_type or "application/octet-stream",
            filename=db_file.filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File download error: {e}")
        raise HTTPException(status_code=500, detail="File download failed")


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
        filename, validated_path = _resolve_upload_path(url, current_user)

        # Check ownership in database
        result = await db.execute(select(FileModel).where(FileModel.unique_filename == filename))
        db_file = result.scalar_one_or_none()

        if not db_file:
            raise HTTPException(status_code=404, detail="File not found")

        # Security: Check ownership before deletion.
        if db_file.user_id != current_user.id:
            logger.warning(
                f"Unauthorized delete attempt by user {mask_user_id(str(current_user.id))} "
                f"on file owned by {mask_user_id(str(db_file.user_id))}"
            )
            raise HTTPException(status_code=403, detail="Not authorized to delete this file")

        if not os.path.exists(validated_path):
            # Reconcile stale metadata without allowing a caller to target an
            # unknown orphan. The ownership row is still checked above.
            await db.delete(db_file)
            await db.commit()
            raise HTTPException(status_code=404, detail="File not found")

        quarantine_path = os.path.join(UPLOAD_DIR, f".deleting-{uuid.uuid4()}-{filename}")
        os.replace(validated_path, quarantine_path)
        try:
            await db.delete(db_file)
            await db.commit()
        except Exception:
            await db.rollback()
            try:
                os.replace(quarantine_path, validated_path)
            except OSError as restore_error:
                logger.error("Failed to restore file after DB delete failure: %s", restore_error)
            raise

        try:
            os.remove(quarantine_path)
        except OSError as cleanup_error:
            # The DB row is gone and the quarantined path is outside the
            # public namespace; a maintenance cleanup can retry this safely.
            logger.warning(
                "Failed to remove quarantined file %s: %s", quarantine_path, cleanup_error
            )
        logger.info(f"File deleted by user {mask_user_id(str(current_user.id))}: {filename}")
        return {"message": "File deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail="File deletion failed")
