"""Private temporary file helper for tool output spillover.

Creates owner-only log files without reusing predictable names.
"""

from __future__ import annotations

import os
import secrets
import tempfile
from typing import Any


def create_private_temp_write_stream(prefix: str) -> dict[str, Any]:
    """Open a unique write stream with owner-only permissions."""
    file_id = secrets.token_hex(8)
    file_path = os.path.join(tempfile.gettempdir(), f"{prefix}-{file_id}.log")
    # Open with exclusive create and owner-only permissions
    fd = os.open(file_path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    stream = os.fdopen(fd, "w")
    return {"path": file_path, "stream": stream}
