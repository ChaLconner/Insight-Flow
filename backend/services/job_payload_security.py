"""Protect short-lived secrets stored in durable background-job payloads."""

from base64 import urlsafe_b64encode
from hashlib import sha256

from cryptography.fernet import Fernet, InvalidToken

from config import get_secret_key


def _cipher() -> Fernet:
    """Build a Fernet cipher from the application secret without persisting a key."""
    key = urlsafe_b64encode(sha256(get_secret_key().encode("utf-8")).digest())
    return Fernet(key)


def encrypt_job_secret(secret: str) -> str:
    """Encrypt a one-time secret before it is written to a job payload."""
    if not isinstance(secret, str) or not secret:
        raise ValueError("Job secret must be a non-empty string")
    return _cipher().encrypt(secret.encode("utf-8")).decode("ascii")


def decrypt_job_secret(protected_secret: str) -> str:
    """Decrypt a protected job secret, normalizing cryptographic failures."""
    if not isinstance(protected_secret, str) or not protected_secret:
        raise ValueError("Protected job secret is missing")
    try:
        return _cipher().decrypt(protected_secret.encode("ascii")).decode("utf-8")
    except (InvalidToken, ValueError) as exc:
        raise ValueError("Protected job secret is invalid") from exc
