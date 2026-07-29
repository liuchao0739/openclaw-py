import os
import re
import uuid
from typing import Optional, TypedDict, Literal
from pathlib import Path

CanvasSnapshotFormat = Literal["png", "jpg", "jpeg"]
CanvasSnapshotFileExtension = Literal["png", "jpg"]


class CanvasSnapshotPayload(TypedDict):
    format: CanvasSnapshotFormat
    base64: str


def _resolve_preferred_openclaw_tmp_dir() -> str:
    tmp_dir = os.environ.get("OPENCLAW_TMP_DIR") or os.environ.get("TMPDIR") or "/tmp"
    return str(Path(tmp_dir))


def _as_record(value):
    if isinstance(value, dict):
        return value
    return {}


def _read_string_value(value) -> Optional[str]:
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    return None


def _normalize_canvas_snapshot_format(value: Optional[str]) -> Optional[CanvasSnapshotFormat]:
    if value is None:
        return None
    fmt = value.strip().lower()
    if fmt in ("png", "jpg", "jpeg"):
        return fmt
    return None


def normalize_canvas_snapshot_file_extension(value: str) -> CanvasSnapshotFileExtension:
    stripped = value[1:] if value.startswith(".") else value
    fmt = _normalize_canvas_snapshot_format(stripped)
    if not fmt:
        raise ValueError("invalid canvas.snapshot format")
    return "jpg" if fmt == "jpeg" else fmt


def parse_canvas_snapshot_payload(value) -> CanvasSnapshotPayload:
    obj = _as_record(value)
    fmt = _normalize_canvas_snapshot_format(_read_string_value(obj.get("format")))
    base64 = _read_string_value(obj.get("base64"))
    if not fmt or not base64:
        raise ValueError("invalid canvas.snapshot payload")
    return {"format": fmt, "base64": base64}


def _resolve_cli_name() -> str:
    return "openclaw"


def _resolve_canvas_snapshot_id(snapshot_id: str) -> str:
    if not re.match(r"^[A-Za-z0-9_-]+$", snapshot_id):
        raise ValueError("invalid canvas snapshot id")
    return snapshot_id


def canvas_snapshot_temp_path(ext: str, tmp_dir: Optional[str] = None, id_value: Optional[str] = None) -> str:
    resolved_tmp_dir = tmp_dir if tmp_dir is not None else _resolve_preferred_openclaw_tmp_dir()
    if tmp_dir is None:
        Path(resolved_tmp_dir).mkdir(parents=True, exist_ok=True, mode=0o700)
    snapshot_id = _resolve_canvas_snapshot_id(id_value if id_value is not None else str(uuid.uuid4()))
    file_ext = "." + normalize_canvas_snapshot_file_extension(ext)
    cli_name = _resolve_cli_name()
    return str(Path(resolved_tmp_dir) / f"{cli_name}-canvas-snapshot-{snapshot_id}{file_ext}")
