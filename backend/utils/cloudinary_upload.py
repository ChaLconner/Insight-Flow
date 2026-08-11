"""
Cloudinary upload utility for handling file uploads to Cloudinary cloud storage.
"""

import logging
import os
from typing import Any

import cloudinary
import cloudinary.uploader
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

logger = logging.getLogger(__name__)


def is_cloudinary_configured() -> bool:
    """
    Check if Cloudinary is properly configured.

    Returns:
        True if all required environment variables are set
    """
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    return all([cloud_name, api_key, api_secret])


# Initialize Cloudinary configuration
def init_cloudinary():
    """
    Initialize Cloudinary with environment variables.
    Should be called once at application startup.
    """
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME")
    api_key = os.getenv("CLOUDINARY_API_KEY")
    api_secret = os.getenv("CLOUDINARY_API_SECRET")

    if not all([cloud_name, api_key, api_secret]):
        logger.warning("Cloudinary credentials not fully configured. File uploads will fail.")
        return False

    cloudinary.config(cloud_name=cloud_name, api_key=api_key, api_secret=api_secret, secure=True)

    logger.info(f"Cloudinary initialized with cloud name: {cloud_name}")
    return True


def upload_avatar(file_content: bytes, filename: str, user_id: str) -> dict[str, Any] | None:
    """
    Upload avatar image to Cloudinary with optimized settings.

    Args:
        file_content: Binary content of the file
        filename: Original filename
        user_id: User ID for organizing uploads

    Returns:
        Dict containing upload result with 'secure_url' and 'public_id', or None if failed
    """
    try:
        # Ensure Cloudinary is configured
        if not is_cloudinary_configured():
            logger.error("Cloudinary is not configured - cannot upload avatar")
            return None

        # Initialize Cloudinary if not already done
        init_cloudinary()

        # Create a unique public_id for the avatar (includes folder path)
        public_id = f"insight-flow/avatars/{user_id}"

        logger.info(f"Uploading avatar to Cloudinary with public_id: {public_id}")

        # OPTIMIZED UPLOAD:
        # - Use eager transformations (process in background, return faster)
        # - Simplified transformation for faster processing
        # - Use invalidate to clear CDN cache immediately
        result = cloudinary.uploader.upload(
            file_content,
            public_id=public_id,
            overwrite=True,
            resource_type="image",
            invalidate=True,  # Clear CDN cache for immediate update
            # Eager transformation - process in background for faster response
            eager=[
                {"width": 200, "height": 200, "crop": "fill", "gravity": "face", "quality": "auto"}
            ],
            eager_async=True,  # Process eagerly in background
            # Add tags for easy management
            tags=["avatar", "user", str(user_id)],
        )

        logger.info(f"Avatar uploaded successfully for user {user_id}: {result.get('secure_url')}")

        return {
            "secure_url": result.get("secure_url"),
            "public_id": result.get("public_id"),
            "width": result.get("width"),
            "height": result.get("height"),
            "format": result.get("format"),
            "bytes": result.get("bytes"),
        }

    except Exception as e:
        # Use exc_info=True to properly log the stack trace
        logger.exception(f"Failed to upload avatar to Cloudinary: {e!s}", exc_info=True)
        return None


def delete_avatar(public_id: str) -> bool:
    """
    Delete an avatar from Cloudinary.

    Args:
        public_id: The public ID of the image to delete

    Returns:
        True if deleted successfully, False otherwise
    """
    try:
        result = cloudinary.uploader.destroy(public_id, resource_type="image")
        success = result.get("result") == "ok"

        if success:
            logger.info(f"Avatar deleted successfully: {public_id}")
        else:
            logger.warning(f"Avatar deletion returned: {result}")

        return bool(success)

    except Exception as e:
        logger.exception(f"Failed to delete avatar from Cloudinary: {e!s}")
        return False


def get_avatar_url(public_id: str, width: int = 200, height: int = 200) -> str:
    """
    Generate a Cloudinary URL for an avatar with transformations.

    Args:
        public_id: The public ID of the image
        width: Desired width
        height: Desired height

    Returns:
        Transformed image URL
    """
    try:
        url, _ = cloudinary.utils.cloudinary_url(
            public_id,
            width=width,
            height=height,
            crop="fill",
            gravity="face",
            quality="auto:good",
            fetch_format="auto",
        )
        return str(url)
    except Exception as e:
        logger.exception(f"Failed to generate Cloudinary URL: {e!s}")
        return ""
