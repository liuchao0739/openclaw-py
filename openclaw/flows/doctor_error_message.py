"""Shared sanitization for doctor/lint/repair errors shown in terminal output.

Mirrors src/flows/doctor-error-message.ts.
"""

from __future__ import annotations

from typing import Any

ERR_MESSAGE_MAX_LEN = 256


def scrub_doctor_error_message(err: Any) -> str:
    """Remove control characters and cap error messages before doctor prints them."""
    raw = str(err)
    stripped = "".join(
        ch for ch in raw if ord(ch) > 0x1F and ord(ch) != 0x7F
    )
    if len(stripped) <= ERR_MESSAGE_MAX_LEN:
        return stripped
    return stripped[: ERR_MESSAGE_MAX_LEN - 3] + "..."
