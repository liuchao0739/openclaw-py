from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional

from .config_utils import normalize_agent_id
from .error_utils import format_error_message, redact_sensitive_text
from .fs_utils import stat_file, walk_files
from .hash import hash_text
from .openclaw_runtime_io import create_subsystem_logger
from .session_file_entry import classify_session_transcript, parse_session_file_entry
from .session_runtime import (
    HEARTBEAT_PROMPT,
    HEARTBEAT_TOKEN,
    SILENT_REPLY_TOKEN,
    has_inter_session_user_provenance,
    is_compaction_checkpoint_transcript_filename,
    is_cron_run_session_key,
    is_exec_completion_event,
    is_heartbeat_user_message,
    is_session_archive_artifact_name,
    is_silent_reply_payload_text,
    is_usage_counted_session_transcript_filename,
    parse_usage_counted_session_id_from_filename,
    resolve_session_transcripts_dir_for_agent,
    strip_inbound_metadata,
    strip_internal_runtime_context,
)
from .session_transcript_corpus import (
    list_session_transcript_corpus_entries_for_agent,
    list_session_transcript_corpus_entries_for_agent_sync,
)


DREAMING_NARRATIVE_RUN_PREFIX = "dreaming-narrative-"
SESSION_EXPORT_CONTENT_WRAP_CHARS = 800
MAX_DATE_TIMESTAMP_MS = 8_640_000_000_000_000
DIRECT_CRON_PROMPT_RE = re.compile(r"^\[cron:[^\]]+\]\s*")
GENERATED_SYSTEM_MESSAGE_RE = re.compile(r"^System(?: \(untrusted\))?: \[[^\]]+\]\s*")


class SessionFileEntry:
    def __init__(
        self,
        path: str,
        abs_path: str,
        mtime_ms: float,
        size: int,
        hash: str,
        content: str,
        line_map: Optional[List[int]] = None,
        message_timestamps_ms: Optional[List[int]] = None,
        generated_by_dreaming_narrative: bool = False,
        generated_by_cron_run: bool = False,
    ):
        self.path = path
        self.abs_path = abs_path
        self.mtime_ms = mtime_ms
        self.size = size
        self.hash = hash
        self.content = content
        self.line_map = line_map or []
        self.message_timestamps_ms = message_timestamps_ms or []
        self.generated_by_dreaming_narrative = generated_by_dreaming_narrative
        self.generated_by_cron_run = generated_by_cron_run


def _should_skip_transcript_file_for_dreaming(abs_path: str) -> bool:
    file_name = os.path.basename(abs_path)
    if is_compaction_checkpoint_transcript_filename(file_name):
        return True
    if is_session_archive_artifact_name(file_name) and not is_usage_counted_session_transcript_filename(file_name):
        return True
    return False


def _is_dreaming_narrative_bootstrap_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if record.get("type") != "custom":
        return False
    if record.get("customType") != "openclaw:bootstrap-context:full":
        return False
    data = record.get("data")
    if not isinstance(data, dict):
        return False
    run_id = data.get("runId")
    return isinstance(run_id, str) and run_id.startswith(DREAMING_NARRATIVE_RUN_PREFIX)


def _has_dreaming_narrative_run_id(value: Any) -> bool:
    return isinstance(value, str) and value.startswith(DREAMING_NARRATIVE_RUN_PREFIX)


def _is_dreaming_narrative_generated_record(record: Any) -> bool:
    if _is_dreaming_narrative_bootstrap_record(record):
        return True
    if not isinstance(record, dict):
        return False
    if _has_dreaming_narrative_run_id(record.get("runId")) or _has_dreaming_narrative_run_id(record.get("sessionKey")):
        return True
    data = record.get("data")
    if not isinstance(data, dict):
        return False
    return _has_dreaming_narrative_run_id(data.get("runId")) or _has_dreaming_narrative_run_id(data.get("sessionKey"))


def _has_cron_run_session_key(value: Any) -> bool:
    return isinstance(value, str) and is_cron_run_session_key(value)


def _is_cron_run_generated_record(record: Any) -> bool:
    if not isinstance(record, dict):
        return False
    if _has_cron_run_session_key(record.get("sessionKey")):
        return True
    data = record.get("data")
    if not isinstance(data, dict):
        return False
    return _has_cron_run_session_key(data.get("sessionKey"))


def _normalize_session_text(value: str) -> str:
    return re.sub(r"\s+", " ", value).strip()


def _collect_raw_session_text(content: Any) -> Optional[str]:
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        parts = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text" and isinstance(block.get("text"), str):
                parts.append(block["text"])
        return "\n".join(parts) if parts else None
    return None


def _sanitize_session_text(text: str, role: str) -> Optional[str]:
    stripped = text
    if role == "user":
        stripped = strip_inbound_metadata(text)
    stripped = strip_internal_runtime_context(stripped)
    normalized = _normalize_session_text(stripped)
    if not normalized:
        return None
    if role == "user" and GENERATED_SYSTEM_MESSAGE_RE.match(normalized):
        return None
    if role == "user" and DIRECT_CRON_PROMPT_RE.match(normalized):
        return None
    if role == "user" and is_heartbeat_user_message({"role": "user", "content": normalized}, HEARTBEAT_PROMPT):
        return None
    if is_silent_reply_payload_text(normalized):
        return None
    if role == "assistant" and normalized == HEARTBEAT_TOKEN:
        return None
    without_system = GENERATED_SYSTEM_MESSAGE_RE.sub("", normalized).strip()
    if is_exec_completion_event(without_system):
        return None
    return normalized


def _parse_session_timestamp_ms(record: Dict[str, Any], message: Dict[str, Any]) -> int:
    candidates = [message.get("timestamp"), record.get("timestamp")]
    for value in candidates:
        if isinstance(value, (int, float)):
            ms = value * 1000 if 0 < value < 1e11 else value
            if 0 < ms <= MAX_DATE_TIMESTAMP_MS:
                return int(ms)
        if isinstance(value, str):
            try:
                from datetime import datetime
                dt = datetime.fromisoformat(value)
                ts = int(dt.timestamp() * 1000)
                if ts > 0:
                    return ts
            except Exception:
                pass
    return 0


def _split_long_session_line(text: str, max_chars: int = SESSION_EXPORT_CONTENT_WRAP_CHARS) -> List[str]:
    normalized = text.strip()
    if not normalized:
        return []
    if len(normalized) <= max_chars:
        return [normalized]

    segments = []
    cursor = 0
    while cursor < len(normalized):
        remaining = len(normalized) - cursor
        if remaining <= max_chars:
            segments.append(normalized[cursor:].strip())
            break

        limit = cursor + max_chars
        split_at = limit
        for idx in range(limit, cursor, -1):
            if normalized[idx] == " ":
                split_at = idx
                break

        segments.append(normalized[cursor:split_at].strip())
        cursor = split_at
        while cursor < len(normalized) and normalized[cursor] == " ":
            cursor += 1

    return [s for s in segments if s]


def _render_session_export_lines(label: str, text: str) -> List[str]:
    return [f"{label}: {segment}" for segment in _split_long_session_line(text)]


def normalize_session_transcript_path_for_comparison(pathname: str) -> str:
    return os.path.realpath(pathname)


def list_session_files_for_agent(agent_id: str) -> List[str]:
    entries = list_session_transcript_corpus_entries_for_agent(agent_id)
    return [entry.get("sessionFile", "") for entry in entries if entry.get("sessionFile")]


def build_session_entry(
    abs_path: str,
    generated_by_dreaming_narrative: Optional[bool] = None,
    generated_by_cron_run: Optional[bool] = None,
) -> Optional[SessionFileEntry]:
    try:
        stat_result = stat_file(abs_path)
        if stat_result is None or not isinstance(stat_result, dict):
            return None

        mtime_ms = stat_result.get("mtimeMs", 0)
        size = stat_result.get("size", 0)

        if _should_skip_transcript_file_for_dreaming(abs_path):
            return SessionFileEntry(
                path=os.path.join("sessions", os.path.basename(abs_path)),
                abs_path=abs_path,
                mtime_ms=mtime_ms,
                size=size,
                hash=hash_text("\n\n"),
                content="",
                line_map=[],
                message_timestamps_ms=[],
            )

        try:
            with open(abs_path, "r", encoding="utf-8") as f:
                raw = f.read()
        except Exception:
            return None

        collected = []
        line_map = []
        message_timestamps_ms = []
        dreaming = generated_by_dreaming_narrative or False
        cron = generated_by_cron_run or False

        jsonl_idx = 0
        line_start = 0
        while line_start <= len(raw):
            newline_idx = raw.find("\n", line_start)
            line_end = len(raw) if newline_idx < 0 else newline_idx
            line = raw[line_start:line_end]
            line_start = len(raw) + 1 if newline_idx < 0 else newline_idx + 1

            if not line.strip():
                continue

            try:
                record = json.loads(line)
            except Exception:
                continue

            if not dreaming and _is_dreaming_narrative_generated_record(record):
                dreaming = True

            if not cron and _is_cron_run_generated_record(record):
                cron = True
                collected = []
                line_map = []
                message_timestamps_ms = []

            if not isinstance(record, dict) or record.get("type") != "message":
                continue

            message = record.get("message")
            if not isinstance(message, dict):
                continue

            role = message.get("role")
            if role not in ("user", "assistant"):
                continue

            if role == "user" and has_inter_session_user_provenance(message):
                continue

            raw_text = _collect_raw_session_text(message.get("content"))
            if raw_text is None:
                continue

            text = _sanitize_session_text(raw_text, role)
            if not text:
                continue

            if dreaming or cron:
                continue

            safe = redact_sensitive_text(text)
            label = "User" if role == "user" else "Assistant"
            rendered_lines = _render_session_export_lines(label, safe)
            timestamp_ms = _parse_session_timestamp_ms(record, message)
            collected.extend(rendered_lines)
            line_map.extend([jsonl_idx + 1] * len(rendered_lines))
            message_timestamps_ms.extend([timestamp_ms] * len(rendered_lines))
            jsonl_idx += 1

        content = "\n".join(collected)
        return SessionFileEntry(
            path=os.path.join("sessions", os.path.basename(abs_path)),
            abs_path=abs_path,
            mtime_ms=mtime_ms,
            size=size,
            hash=hash_text(content),
            content=content,
            line_map=line_map,
            message_timestamps_ms=message_timestamps_ms,
            generated_by_dreaming_narrative=dreaming,
            generated_by_cron_run=cron,
        )
    except Exception as err:
        logger = create_subsystem_logger("memory")
        logger.debug(f"Failed reading session file {abs_path}: {format_error_message(err)}")
        return None
