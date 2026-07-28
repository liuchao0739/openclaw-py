from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional

from .config_utils import normalize_agent_id
from .session_runtime import (
    canonicalize_main_session_alias,
    is_cron_run_session_key,
    is_session_archive_artifact_name,
    is_usage_counted_session_transcript_filename,
    list_session_entries,
    parse_usage_counted_session_id_from_filename,
    resolve_session_agent_id,
    resolve_session_file_path,
    resolve_store_path,
)


DREAMING_NARRATIVE_RUN_PREFIX = "dreaming-narrative-"


def _is_dreaming_narrative_session_store_key(session_key: str) -> bool:
    trimmed = session_key.strip()
    if not trimmed:
        return False
    first_sep = trimmed.find(":")
    if first_sep < 0:
        return trimmed.startswith(DREAMING_NARRATIVE_RUN_PREFIX)
    second_sep = trimmed.find(":", first_sep + 1)
    session_segment = trimmed if second_sep < 0 else trimmed[second_sep + 1:]
    return session_segment.startswith(DREAMING_NARRATIVE_RUN_PREFIX)


def _normalize_comparable_path(pathname: str) -> str:
    resolved = os.path.realpath(pathname)
    return resolved


def _extract_agent_id_from_session_path(abs_path: str) -> Optional[str]:
    parts = os.path.normpath(os.path.resolve(abs_path)).split(os.sep)
    sessions_idx = len(parts) - 1
    if sessions_idx < 2 or parts[sessions_idx - 2] != "agents":
        return None
    return parts[sessions_idx - 1] or None


def _extract_agent_id_from_sessions_dir(sessions_dir: str) -> Optional[str]:
    parts = os.path.normpath(os.path.resolve(sessions_dir)).split(os.sep)
    sessions_idx = len(parts) - 1
    if parts[sessions_idx] != "sessions" or sessions_idx < 2 or parts[sessions_idx - 2] != "agents":
        return None
    return parts[sessions_idx - 1] or None


def _read_parent_session_keys(entry: Optional[Dict[str, Any]]) -> List[str]:
    keys = set()
    if not entry:
        return []
    for value in [entry.get("parentSessionKey"), entry.get("spawnedBy")]:
        if isinstance(value, str) and value.strip():
            keys.add(value.strip())
    return list(keys)


def _collect_cron_generated_session_keys(summaries: List[Dict[str, Any]]) -> set:
    entries_by_key = {s["sessionKey"]: s.get("entry", {}) for s in summaries}
    cron_generated = set()
    cache = {}

    def _is_cron_generated(session_key: str, entry: Optional[Dict[str, Any]]) -> bool:
        if is_cron_run_session_key(session_key):
            cache[session_key] = True
            cron_generated.add(session_key)
            return True
        if session_key in cache:
            return cache[session_key]
        generated = any(
            is_cron_run_session_key(parent) or _is_cron_generated(parent, entries_by_key.get(parent))
            for parent in _read_parent_session_keys(entry)
        )
        cache[session_key] = generated
        if generated:
            cron_generated.add(session_key)
        return generated

    for summary in summaries:
        _is_cron_generated(summary["sessionKey"], summary.get("entry"))
    return cron_generated


def _list_session_transcript_artifact_files(sessions_dir: str) -> List[str]:
    try:
        files = os.listdir(sessions_dir)
        results = []
        for name in files:
            full_path = os.path.join(sessions_dir, name)
            if os.path.isfile(full_path) and is_usage_counted_session_transcript_filename(name):
                results.append(full_path)
        return results
    except OSError:
        return []


def list_session_transcript_corpus_entries_for_agent_sync(agent_id: str) -> List[Dict[str, Any]]:
    normalized_agent_id = normalize_agent_id(agent_id)
    sessions_dir = os.path.join(os.path.expanduser("~/.openclaw"), "agents", normalized_agent_id, "sessions")
    os.makedirs(sessions_dir, exist_ok=True)

    session_entries = list_session_entries({"agentId": normalized_agent_id})
    cron_generated = _collect_cron_generated_session_keys(
        [{"sessionKey": e.get("sessionKey", ""), "entry": e} for e in session_entries]
    )

    corpus_entries = []
    seen_paths = set()

    for entry in session_entries:
        session_key = entry.get("sessionKey", "")
        session_file = entry.get("sessionFile", "")
        session_id = entry.get("sessionId", "")
        if not session_id and session_file:
            session_id = parse_usage_counted_session_id_from_filename(os.path.basename(session_file)) or ""
        if not session_id:
            continue

        classification = {
            "generatedByDreamingNarrative": _is_dreaming_narrative_session_store_key(session_key),
            "generatedByCronRun": session_key in cron_generated,
        }

        corpus_entry = {
            "agentId": normalized_agent_id,
            "artifactKind": "active-session",
            "sessionFile": session_file or os.path.join(sessions_dir, f"{session_id}.jsonl"),
            "sessionId": session_id,
        }
        if session_key:
            corpus_entry["sessionKey"] = session_key
        if classification["generatedByDreamingNarrative"]:
            corpus_entry["generatedByDreamingNarrative"] = True
        if classification["generatedByCronRun"]:
            corpus_entry["generatedByCronRun"] = True

        path_key = _normalize_comparable_path(corpus_entry["sessionFile"])
        if path_key not in seen_paths:
            seen_paths.add(path_key)
            corpus_entries.append(corpus_entry)

    for artifact_path in _list_session_transcript_artifact_files(sessions_dir):
        path_key = _normalize_comparable_path(artifact_path)
        if path_key in seen_paths:
            continue
        seen_paths.add(path_key)

        session_id = parse_usage_counted_session_id_from_filename(os.path.basename(artifact_path))
        if not session_id:
            continue

        kind = "archive-artifact" if is_session_archive_artifact_name(os.path.basename(artifact_path)) else "orphan-file-artifact"
        corpus_entries.append({
            "agentId": normalized_agent_id,
            "artifactKind": kind,
            "sessionFile": artifact_path,
            "sessionId": session_id,
        })

    return corpus_entries


def list_session_transcript_corpus_entries_for_agent(agent_id: str) -> List[Dict[str, Any]]:
    return list_session_transcript_corpus_entries_for_agent_sync(agent_id)
