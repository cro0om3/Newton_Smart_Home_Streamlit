"""Helpers for normalizing product image Base64 values.

All functions here ensure that image values provided by data sources
are returned as data URIs (data:image/...;base64,...) or `None`.

Important: per requirements we do NOT load filesystem paths or URLs.
If a value looks like an http(s) URL or a file path it will be ignored
and `None` will be returned.
"""
from typing import Optional, Any


def ensure_data_url(value: Any) -> Optional[str]:
    """Normalize an image value to a data URI or return None.

    - If `value` already starts with `data:` it is returned as-is.
    - If `value` is an http(s) or file URL it is rejected (return None).
    - Otherwise the string is treated as raw Base64 and prefixed with
      `data:image/png;base64,` (defaulting to PNG when no prefix present).
    """
    if value is None:
        return None
    s = str(value).strip()
    if not s:
        return None
    low = s.lower()
    # Keep existing data URIs
    if low.startswith("data:"):
        return s
    # Reject external URLs or file paths per requirement
    if low.startswith("http://") or low.startswith("https://") or low.startswith("file://"):
        return None
    # Otherwise assume raw base64 content; remove whitespace/newlines
    cleaned = "".join(s.split())
    if not cleaned:
        return None
    return f"data:image/png;base64,{cleaned}"


__all__ = ["ensure_data_url"]
