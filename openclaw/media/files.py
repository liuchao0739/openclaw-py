"""Media file helpers."""

from __future__ import annotations

import base64
import mimetypes
from dataclasses import dataclass
from pathlib import Path


@dataclass
class MediaAttachment:
    filename: str
    mime_type: str
    data_base64: str


def load_attachment(path: str | Path) -> MediaAttachment:
    file_path = Path(path)
    mime_type = mimetypes.guess_type(file_path.name)[0] or "application/octet-stream"
    encoded = base64.b64encode(file_path.read_bytes()).decode("ascii")
    return MediaAttachment(filename=file_path.name, mime_type=mime_type, data_base64=encoded)


def save_attachment(path: str | Path, attachment: MediaAttachment) -> Path:
    file_path = Path(path)
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(base64.b64decode(attachment.data_base64))
    return file_path
