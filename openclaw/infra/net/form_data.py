"""FormData detection helper.

Mirrors src/infra/net/form-data.ts.
"""

from __future__ import annotations

from typing import Any


def is_form_data_like(value: Any) -> bool:
    """Check if a value is FormData-like."""
    if value is None or not isinstance(value, object):
        return False
    entries = getattr(value, "entries", None)
    if not callable(entries):
        return False
    tag = getattr(value, "_isFormData", None)
    if tag is True:
        return True
    # Check for FormData class name as fallback
    return type(value).__name__ == "FormData"
