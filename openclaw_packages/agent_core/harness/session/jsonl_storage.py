from __future__ import annotations

import json
import time
from dataclasses import asdict
from typing import Any

from ..harness_types import (
    FileError,
    JsonlSessionMetadata,
    SessionError,
    SessionTreeEntry,
)
from .storage_base import (
    BaseSessionStorage,
    append_parent_id_after_entry,
    leaf_id_update_after_entry,
)
from .timestamps import parse_session_timestamp_ms
from .uuid import uuidv7


def _get_fs_result_or_throw(
    result: dict[str, Any],
    message: str,
) -> Any:
    if not result.get("ok", False):
        error = result.get("error")
        code = "not_found" if error and error.get("code") == "not_found" else "storage"
        raise SessionError(code, f"{message}: {error.get('message') if error else 'unknown error'}")
    return result.get("value")


def _invalid_session(file_path: str, message: str, cause: Exception | None = None) -> SessionError:
    return SessionError(
        "invalid_session",
        f"Invalid JSONL session file {file_path}: {message}",
        cause,
    )


def _invalid_entry(
    file_path: str,
    line_number: int,
    message: str,
    cause: Exception | None = None,
) -> SessionError:
    return SessionError(
        "invalid_entry",
        f"Invalid JSONL session file {file_path}: line {line_number} {message}",
        cause,
    )


def _parse_header_line(line: str, file_path: str) -> dict[str, Any]:
    try:
        parsed = json.loads(line)
    except (ValueError, TypeError) as error:
        raise _invalid_session(file_path, "first line is not a valid session header", Exception(str(error)))
    if not isinstance(parsed, dict):
        raise _invalid_session(file_path, "first line is not a valid session header")
    if parsed.get("type") != "session":
        raise _invalid_session(file_path, "first line is not a valid session header")
    if parsed.get("version") != 3:
        raise _invalid_session(file_path, "unsupported session version")
    if not isinstance(parsed.get("id"), str) or not parsed.get("id"):
        raise _invalid_session(file_path, "session header is missing id")
    if not isinstance(parsed.get("timestamp"), str) or not parsed.get("timestamp"):
        raise _invalid_session(file_path, "session header is missing timestamp")
    if parse_session_timestamp_ms(parsed["timestamp"]) is None:
        raise _invalid_session(file_path, "session header has invalid timestamp")
    if not isinstance(parsed.get("cwd"), str) or not parsed.get("cwd"):
        raise _invalid_session(file_path, "session header is missing cwd")
    parent_session = parsed.get("parentSession")
    if parent_session is not None and not isinstance(parent_session, str):
        raise _invalid_session(file_path, "session header parentSession must be a string")
    return {
        "type": "session",
        "version": 3,
        "id": parsed["id"],
        "timestamp": parsed["timestamp"],
        "cwd": parsed["cwd"],
        "parentSession": parent_session,
    }


def _parse_entry_line(line: str, file_path: str, line_number: int) -> SessionTreeEntry:
    try:
        parsed = json.loads(line)
    except (ValueError, TypeError) as error:
        raise _invalid_entry(file_path, line_number, "is not valid JSON", Exception(str(error)))
    if not isinstance(parsed, dict):
        raise _invalid_entry(file_path, line_number, "is not a valid session entry")
    if not isinstance(parsed.get("type"), str):
        raise _invalid_entry(file_path, line_number, "is missing entry type")
    if not isinstance(parsed.get("id"), str) or not parsed.get("id"):
        raise _invalid_entry(file_path, line_number, "is missing entry id")
    parent_id = parsed.get("parentId")
    if parent_id is not None and not isinstance(parent_id, str):
        raise _invalid_entry(file_path, line_number, "has invalid parentId")
    if not isinstance(parsed.get("timestamp"), str) or not parsed.get("timestamp"):
        raise _invalid_entry(file_path, line_number, "is missing timestamp")
    if parse_session_timestamp_ms(parsed["timestamp"]) is None:
        raise _invalid_entry(file_path, line_number, "has invalid timestamp")
    if parsed.get("type") == "leaf":
        target_id = parsed.get("targetId")
        if target_id is not None and not isinstance(target_id, str):
            raise _invalid_entry(file_path, line_number, "has invalid targetId")
        append_parent_id = parsed.get("appendParentId")
        if append_parent_id is not None and append_parent_id is not None and not isinstance(append_parent_id, str):
            raise _invalid_entry(file_path, line_number, "has invalid appendParentId")
    append_mode = parsed.get("appendMode")
    if append_mode is not None and append_mode != "side":
        raise _invalid_entry(file_path, line_number, "has invalid appendMode")
    return parsed


def _header_to_session_metadata(header: dict[str, Any], path: str) -> JsonlSessionMetadata:
    return JsonlSessionMetadata(
        id=header["id"],
        createdAt=header["timestamp"],
        cwd=header["cwd"],
        path=path,
        parentSessionPath=header.get("parentSession"),
    )


async def load_jsonl_session_metadata(
    fs: Any,
    file_path: str,
) -> JsonlSessionMetadata:
    result = await fs.readTextLines(file_path, {"maxLines": 1})
    lines = _get_fs_result_or_throw(result, f"Failed to read session header {file_path}")
    line = lines[0] if lines else None
    if line and line.strip():
        return _header_to_session_metadata(_parse_header_line(line, file_path), file_path)
    raise _invalid_session(file_path, "missing session header")


async def _load_jsonl_storage(
    fs: Any,
    file_path: str,
) -> dict[str, Any]:
    result = await fs.readTextFile(file_path)
    content = _get_fs_result_or_throw(result, f"Failed to read session {file_path}")
    lines = [line for line in content.split("\n") if line.strip()]
    if not lines:
        raise _invalid_session(file_path, "missing session header")

    header = _parse_header_line(lines[0], file_path)
    entries: list[SessionTreeEntry] = []
    leaf_id: str | None = None
    append_parent_id: str | None = None
    for i in range(1, len(lines)):
        entry = _parse_entry_line(lines[i], file_path, i + 1)
        entries.append(entry)
        leaf_update = leaf_id_update_after_entry(entry)
        if leaf_update is not None:
            leaf_id = leaf_update
        append_parent_id = append_parent_id_after_entry(entry)
    return {
        "header": header,
        "entries": entries,
        "leafId": leaf_id,
        "appendParentId": append_parent_id,
    }


class JsonlSessionStorage(BaseSessionStorage):
    def __init__(
        self,
        fs: Any,
        file_path: str,
        header: dict[str, Any],
        entries: list[SessionTreeEntry],
        leaf_id: str | None,
        append_parent_id: str | None,
    ) -> None:
        metadata = _header_to_session_metadata(header, file_path)
        super().__init__(metadata, entries, leaf_id, append_parent_id)
        self._fs = fs
        self._file_path = file_path

    @classmethod
    async def open(cls, fs: Any, file_path: str) -> "JsonlSessionStorage":
        loaded = await _load_jsonl_storage(fs, file_path)
        return cls(
            fs,
            file_path,
            loaded["header"],
            loaded["entries"],
            loaded["leafId"],
            loaded["appendParentId"],
        )

    @classmethod
    async def create(
        cls,
        fs: Any,
        file_path: str,
        options: dict[str, Any],
    ) -> "JsonlSessionStorage":
        from datetime import datetime, timezone
        header = {
            "type": "session",
            "version": 3,
            "id": options["sessionId"],
            "timestamp": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
            "cwd": options["cwd"],
            "parentSession": options.get("parentSessionPath"),
        }
        result = await fs.writeFile(file_path, json.dumps(header) + "\n")
        _get_fs_result_or_throw(result, f"Failed to create session {file_path}")
        return cls(fs, file_path, header, [], None, None)

    async def set_leaf_id(self, leaf_id: str | None) -> None:
        entry = self._create_leaf_entry(leaf_id)
        result = await self._fs.appendFile(self._file_path, json.dumps(entry) + "\n")
        _get_fs_result_or_throw(result, f"Failed to append session leaf {entry.id}")
        self._record_entry(entry)

    async def append_entry(self, entry: SessionTreeEntry) -> None:
        self._validate_entry_for_append(entry)
        result = await self._fs.appendFile(self._file_path, json.dumps(_entry_to_dict(entry)) + "\n")
        _get_fs_result_or_throw(result, f"Failed to append session entry {entry.id}")
        self._record_entry(entry)


def _entry_to_dict(entry: SessionTreeEntry) -> dict[str, Any]:
    if hasattr(entry, "__dataclass_fields__"):
        return asdict(entry)
    return dict(entry)
