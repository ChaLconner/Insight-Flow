"""
File Upload Security Utilities.
Centralized security validation for all file uploads.
"""

import os
import re

from utils.logger import setup_logger

logger = setup_logger("file_security")

# =============================================================================
# Avatar Upload Configuration (Images Only)
# =============================================================================

AVATAR_ALLOWED_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
}

AVATAR_ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
}

AVATAR_MAX_FILE_SIZE_BYTES: int = 5 * 1024 * 1024  # 5 MB for avatars

# =============================================================================
# General File Upload Configuration
# =============================================================================

ALLOWED_EXTENSIONS: set[str] = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",  # Images
    ".pdf",  # Documents
    ".doc",
    ".docx",
    ".xls",
    ".xlsx",
    ".ppt",
    ".pptx",  # Office
    ".txt",
    ".csv",
    ".md",  # Text
}

ALLOWED_MIME_TYPES: dict[str, set[str]] = {
    "image/jpeg": {".jpg", ".jpeg"},
    "image/png": {".png"},
    "image/gif": {".gif"},
    "image/webp": {".webp"},
    "application/pdf": {".pdf"},
    "application/msword": {".doc"},
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {".docx"},
    "application/vnd.ms-excel": {".xls"},
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet": {".xlsx"},
    "application/vnd.ms-powerpoint": {".ppt"},
    "application/vnd.openxmlformats-officedocument.presentationml.presentation": {".pptx"},
    "text/plain": {".txt", ".csv", ".md"},
    "text/csv": {".csv"},
    "text/markdown": {".md"},
}

MAX_FILE_SIZE_BYTES: int = 10 * 1024 * 1024  # 10 MB

# =============================================================================
# Dangerous Patterns (for filename sanitization)
# =============================================================================

# Patterns that could indicate malicious filenames
DANGEROUS_PATTERNS = [
    r"\.\.",  # Directory traversal
    r"[\x00-\x1f]",  # Control characters
    r"[<>:\"|?*]",  # Windows forbidden characters
    r"^\.+$",  # All dots
    r"[\\/]",  # Path separators
]


class FileSecurityError(Exception):
    """Exception raised for file security validation failures."""

    def __init__(self, message: str, error_code: str = "FILE_SECURITY_ERROR"):
        self.message = message
        self.error_code = error_code
        super().__init__(self.message)


def validate_extension(
    filename: str | None,
    allowed_extensions: set[str] | None = None,
) -> str:
    """
    Validate and return the file extension.

    Args:
        filename: Original filename
        allowed_extensions: Set of allowed extensions (defaults to ALLOWED_EXTENSIONS)

    Returns:
        Validated lowercase file extension

    Raises:
        FileSecurityError: If extension is not allowed
    """
    if not filename:
        raise FileSecurityError("Filename is required", "MISSING_FILENAME")

    extensions = allowed_extensions or ALLOWED_EXTENSIONS
    ext = os.path.splitext(filename)[1].lower()

    if not ext:
        raise FileSecurityError("File must have an extension", "MISSING_EXTENSION")

    if ext not in extensions:
        allowed_list = ", ".join(sorted(extensions))
        raise FileSecurityError(
            f"File type '{ext}' not allowed. Allowed types: {allowed_list}", "INVALID_EXTENSION"
        )

    return ext


def validate_mime_type(
    content_type: str | None,
    extension: str,
    allowed_mime_types: dict[str, set[str]] | None = None,
) -> None:
    """
    Validate that MIME type matches the file extension.

    Args:
        content_type: MIME type from the upload
        extension: File extension (already validated)
        allowed_mime_types: Dict mapping MIME types to extensions

    Raises:
        FileSecurityError: If MIME type is invalid or doesn't match extension
    """
    if not content_type:
        raise FileSecurityError("Content type is required", "MISSING_CONTENT_TYPE")

    mime_types = allowed_mime_types or ALLOWED_MIME_TYPES

    # Check if MIME type is in our whitelist
    if content_type not in mime_types:
        raise FileSecurityError(
            f"Content type '{content_type}' not allowed", "INVALID_CONTENT_TYPE"
        )

    # Verify extension matches MIME type
    allowed_extensions = mime_types[content_type]
    if extension not in allowed_extensions:
        raise FileSecurityError(
            f"File extension '{extension}' does not match content type '{content_type}'",
            "MIME_EXTENSION_MISMATCH",
        )


def validate_file_size(
    content: bytes,
    max_size: int | None = None,
) -> int:
    """
    Validate file size.

    Args:
        content: File content as bytes
        max_size: Maximum allowed size in bytes

    Returns:
        File size in bytes

    Raises:
        FileSecurityError: If file is too large or empty
    """
    max_allowed = max_size or MAX_FILE_SIZE_BYTES
    size = len(content)

    if size == 0:
        raise FileSecurityError("Empty file not allowed", "EMPTY_FILE")

    if size > max_allowed:
        max_mb = max_allowed / (1024 * 1024)
        raise FileSecurityError(
            f"File too large. Maximum size is {max_mb:.1f} MB", "FILE_TOO_LARGE"
        )

    return size


def validate_file_path(base_dir: str, file_path: str) -> str:
    """
    Validate file path to prevent directory traversal attacks.

    Args:
        base_dir: Base directory that file must be within
        file_path: Proposed file path

    Returns:
        Normalized absolute path if valid

    Raises:
        FileSecurityError: If path traversal is detected
    """
    # Normalize both paths
    base_dir_abs = os.path.normpath(os.path.abspath(base_dir))
    file_path_abs = os.path.normpath(os.path.abspath(file_path))

    # Ensure the file path starts with the base directory
    if not file_path_abs.startswith(base_dir_abs + os.sep) and file_path_abs != base_dir_abs:
        logger.warning(f"Path traversal attempt detected: {file_path}")
        raise FileSecurityError("Invalid file path", "PATH_TRAVERSAL_DETECTED")

    return file_path_abs


def sanitize_filename(filename: str) -> str:
    """
    Sanitize a filename to remove potentially dangerous characters.

    Args:
        filename: Original filename

    Returns:
        Sanitized filename
    """
    if not filename:
        return ""

    # Check for dangerous patterns
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, filename):
            logger.warning(f"Dangerous pattern detected in filename: {filename}")
            # Remove the dangerous parts
            filename = re.sub(pattern, "", filename)

    # Only allow alphanumeric, dash, underscore, and dot
    filename = re.sub(r"[^a-zA-Z0-9._-]", "_", filename)

    # Limit length
    if len(filename) > 255:
        name, ext = os.path.splitext(filename)
        filename = name[: 255 - len(ext)] + ext

    return filename


def validate_avatar_upload(
    filename: str | None,
    content_type: str | None,
    content: bytes,
) -> tuple[str, int]:
    """
    Validate an avatar upload with avatar-specific rules.

    Args:
        filename: Original filename
        content_type: MIME type
        content: File content

    Returns:
        Tuple of (validated_extension, file_size)

    Raises:
        FileSecurityError: If any validation fails
    """
    # Validate extension (images only for avatars)
    extension = validate_extension(filename, AVATAR_ALLOWED_EXTENSIONS)

    # Validate MIME type
    validate_mime_type(content_type, extension, AVATAR_ALLOWED_MIME_TYPES)

    # Validate file size (smaller limit for avatars)
    file_size = validate_file_size(content, AVATAR_MAX_FILE_SIZE_BYTES)

    logger.debug(f"Avatar upload validated: extension={extension}, size={file_size}")

    return extension, file_size


def validate_general_upload(
    filename: str | None,
    content_type: str | None,
    content: bytes,
) -> tuple[str, int]:
    """
    Validate a general file upload.

    Args:
        filename: Original filename
        content_type: MIME type
        content: File content

    Returns:
        Tuple of (validated_extension, file_size)

    Raises:
        FileSecurityError: If any validation fails
    """
    # Validate extension
    extension = validate_extension(filename)

    # Validate MIME type
    validate_mime_type(content_type, extension)

    # Validate file size
    file_size = validate_file_size(content)

    logger.debug(f"File upload validated: extension={extension}, size={file_size}")

    return extension, file_size
