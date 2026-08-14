"""
File upload router with security hardening.
Implements: extension whitelist, MIME validation, size limits, path traversal protection.

Security features are centralized in utils/file_security.py
"""

import asyncio
import os
import uuid
from pathlib import Path
from typing import Any

from fastapi import APIRouter, Depends, File, HTTPException, UploadFile, status
from fastapi.responses import FileResponse
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import get_settings
from database import get_async_db
from models.file import File as FileModel
from models.user import User
from routers.auth import get_current_active_user
from utils.file_security import (
    MAX_FILE_SIZE_BYTES,
    FileSecurityError,
    stream_upload_to_tempfile,
    validate_file_path,
    validate_general_upload_path,
)
from utils.logger import mask_user_id, setup_logger

logger = setup_logger("files_router")

router = APIRouter(prefix="/files", tags=["files"])

UPLOAD_DIR = str(Path(__file__).resolve().parent.parent / "storage" / "private_uploads")
DOWNLOAD_URL_PREFIX = "/api/v1/files/download"
INVALID_FILE_PATH_DETAIL = "Invalid file path"
FILE_NOT_FOUND_DETAIL = "File not found"
FILE_ERROR_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"description": "Invalid file request"},
    403: {"description": "The authenticated user does not own the file"},
    404: {"description": "File not found"},
    413: {"description": "The user's file storage quota is exceeded"},
    500: {"description": "File operation failed"},
}

# Ensure upload directory exists
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _read_and_validate_upload(file: UploadFile, current_user: User) -> tuple[str, str, int]:
    """Stage an upload on disk within limits and validate its detected type."""
    try:
        staged_path, streamed_size = await stream_upload_to_tempfile(file, MAX_FILE_SIZE_BYTES)
    except FileSecurityError as e:
        logger.warning(
            f"File upload security violation by user {mask_user_id(str(current_user.id))}: {e.message}"
        )
        raise HTTPException(status_code=400, detail=e.message) from e

    try:
        file_extension, file_size = validate_general_upload_path(
            filename=file.filename,
            content_type=file.content_type,
            file_path=staged_path,
            file_size=streamed_size,
        )
    except FileSecurityError as e:
        _cleanup_upload(staged_path, False, "rejected")
        logger.warning(
            f"File upload security violation by user {mask_user_id(str(current_user.id))}: {e.message}"
        )
        raise HTTPException(status_code=400, detail=e.message) from e
    except Exception:
        _cleanup_upload(staged_path, False, "validation failure")
        raise
    return staged_path, file_extension, file_size


def _cleanup_upload(path: str | None, file_committed: bool, error_type: str) -> None:
    """Remove a partially written upload after a failed request."""
    if file_committed or not path or not os.path.exists(path):
        return
    try:
        os.remove(path)
    except OSError as cleanup_error:
        logger.warning(f"Failed to remove {error_type} upload: {cleanup_error}")


async def _ensure_upload_quota(
    db: AsyncSession,
    user_id: Any,
    incoming_size: int,
) -> None:
    """Reject aggregate storage growth beyond the configured per-user quota."""
    quota_bytes = get_settings().file_upload_quota_bytes
    # Serialize the sum-and-insert sequence across concurrent workers.
    await db.scalar(select(User.id).where(User.id == user_id).with_for_update())
    used_bytes = int(
        await db.scalar(
            select(func.coalesce(func.sum(FileModel.size_bytes), 0)).where(
                FileModel.user_id == user_id
            )
        )
        or 0
    )
    if used_bytes + incoming_size > quota_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail="File storage quota exceeded",
        )


@router.post("/upload", responses=FILE_ERROR_RESPONSES)
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
    staged_path: str | None = None
    validated_path: str | None = None
    file_committed = False
    try:
        # Stream to a bounded temporary file so concurrent uploads do not
        # multiply near-limit request bodies in process memory.
        staged_path, file_extension, file_size = await _read_and_validate_upload(file, current_user)
        await _ensure_upload_quota(db, current_user.id, file_size)

        # Generate unique filename with validated extension
        unique_name = f"{uuid.uuid4()}{file_extension}"
        file_path = os.path.join(UPLOAD_DIR, unique_name)

        # Validate the final path to prevent directory traversal
        try:
            validated_path = validate_file_path(UPLOAD_DIR, file_path)
        except FileSecurityError:
            logger.warning(f"Path traversal attempt by user {mask_user_id(str(current_user.id))}")
            raise HTTPException(status_code=400, detail=INVALID_FILE_PATH_DETAIL)

        # Atomically promote the validated staged file into the private upload
        # directory. No request-sized bytes are retained in Python memory.
        await asyncio.to_thread(os.replace, staged_path, validated_path)
        staged_path = None

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
        _cleanup_upload(staged_path, False, "rejected")
        _cleanup_upload(validated_path, file_committed, "rejected")
        raise
    except Exception as e:
        await db.rollback()
        _cleanup_upload(staged_path, False, "incomplete")
        _cleanup_upload(validated_path, file_committed, "incomplete")
        logger.exception(f"File upload error: {e}")
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
        raise HTTPException(status_code=400, detail=INVALID_FILE_PATH_DETAIL)

    filename = os.path.basename(url)
    if not filename or ".." in filename or "/" in filename or "\\" in filename:
        logger.warning(
            f"Suspicious file path by user {mask_user_id(str(current_user.id))}: {url[:50]}"
        )
        raise HTTPException(status_code=400, detail=INVALID_FILE_PATH_DETAIL)

    file_path = os.path.join(UPLOAD_DIR, filename)
    try:
        validated_path = validate_file_path(UPLOAD_DIR, file_path)
    except FileSecurityError:
        raise HTTPException(status_code=400, detail=INVALID_FILE_PATH_DETAIL)

    return filename, validated_path


@router.get("/info", responses=FILE_ERROR_RESPONSES)
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
            raise HTTPException(status_code=404, detail=FILE_NOT_FOUND_DETAIL)

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
        logger.exception(f"File info error: {e}")
        raise HTTPException(status_code=500, detail="File info lookup failed")


@router.get("/download/{filename}", responses=FILE_ERROR_RESPONSES)
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
            raise HTTPException(status_code=404, detail=FILE_NOT_FOUND_DETAIL)
        if db_file.user_id != current_user.id:
            logger.warning(
                f"Unauthorized file download attempt by user {mask_user_id(str(current_user.id))} "
                f"on file owned by {mask_user_id(str(db_file.user_id))}"
            )
            raise HTTPException(status_code=403, detail="Not authorized to access this file")
        if not os.path.exists(validated_path):
            raise HTTPException(status_code=404, detail=FILE_NOT_FOUND_DETAIL)

        return FileResponse(
            validated_path,
            media_type=db_file.mime_type or "application/octet-stream",
            filename=db_file.filename,
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"File download error: {e}")
        raise HTTPException(status_code=500, detail="File download failed")


@router.delete("/delete", responses=FILE_ERROR_RESPONSES)
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
            raise HTTPException(status_code=404, detail=FILE_NOT_FOUND_DETAIL)

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
            raise HTTPException(status_code=404, detail=FILE_NOT_FOUND_DETAIL)

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
                logger.exception(
                    "Failed to restore file after DB delete failure: %s", restore_error
                )
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
        logger.exception(f"File delete error: {e}")
        raise HTTPException(status_code=500, detail="File deletion failed")
