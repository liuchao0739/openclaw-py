from __future__ import annotations

import os
import re
from typing import Any, Dict, List, Optional

HEARTBEAT_PROMPT = "HEARTBEAT_PROMPT"
HEARTBEAT_TOKEN = "HEARTBEAT_TOKEN"
SILENT_REPLY_TOKEN = "SILENT_REPLY_TOKEN"


def _noop(*args, **kwargs):
    return None


def is_heartbeat_user_message(message: Dict[str, Any], prompt: str) -> bool:
    content = message.get("content", "")
    return prompt in str(content)


def is_silent_reply_payload_text(text: str) -> bool:
    return SILENT_REPLY_TOKEN in str(text)


def strip_inbound_metadata(text: str) -> str:
    return text


def strip_internal_runtime_context(text: str) -> str:
    return text


def is_compaction_checkpoint_transcript_filename(filename: str) -> bool:
    return ".compaction" in filename


def is_session_archive_artifact_name(filename: str) -> bool:
    return bool(re.search(r'\.(bak|reset|deleted)\.', filename))


def is_usage_counted_session_transcript_filename(filename: str) -> bool:
    return is_session_archive_artifact_name(filename) or filename.endswith(".jsonl")


def parse_usage_counted_session_id_from_filename(filename: str) -> Optional[str]:
    match = re.match(r'^(.+?)\.(?:reset|deleted|bak)\.', filename)
    if match:
        return match.group(1)
    if filename.endswith(".jsonl"):
        return filename[:-len(".jsonl")]
    return None


def canonicalize_main_session_alias(cfg: dict, agent_id: str, session_key: str) -> str:
    return session_key


def list_session_entries(params: dict) -> List[Dict[str, Any]]:
    return []


def resolve_session_file_path(session_id: str, session_file: Optional[str] = None, opts: Optional[dict] = None) -> str:
    if session_file:
        return session_file
    sessions_dir = (opts or {}).get("sessionsDir", "")
    return os.path.join(sessions_dir, f"{session_id}.jsonl")


def resolve_store_path(store: object, opts: Optional[dict] = None) -> str:
    agent_id = (opts or {}).get("agentId", "main")
    state_dir = os.path.expanduser("~/.openclaw")
    return os.path.join(state_dir, "agents", agent_id, "sessions", "sessions.json")


def resolve_session_agent_id(config: dict, session_key: str, fallback_agent_id: Optional[str] = None) -> str:
    return fallback_agent_id or "main"


def is_cron_run_session_key(session_key: str) -> bool:
    return "cron" in session_key.lower()


def is_exec_completion_event(message: Dict[str, Any]) -> bool:
    content = message.get("content", "")
    return "[exec:" in str(content) and "] COMPLETED" in str(content)


def on_session_transcript_update(handler: callable) -> None:
    pass


def has_inter_session_user_provenance(message: Dict[str, Any]) -> bool:
    provenance = message.get("provenance")
    if isinstance(provenance, dict):
        return provenance.get("type") == "inter-session"
    return False
