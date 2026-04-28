"""Shared helpers for low-cardinality request path labels."""

import re

_UUID_PATTERN = re.compile(
    r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}",
    flags=re.IGNORECASE,
)
_NUMERIC_ID_PATTERN = re.compile(r"/\d+(?=/|$)")


def normalize_request_path(path: str) -> str:
    """Replace path IDs with placeholders for metrics and tracing."""
    path = _UUID_PATTERN.sub("{id}", path)
    return _NUMERIC_ID_PATTERN.sub("/{id}", path)
