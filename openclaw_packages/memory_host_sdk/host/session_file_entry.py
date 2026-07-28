from __future__ import annotations

from typing import Any, Dict, List, Optional


def resolve_file_entry_path_parts(entry: Dict[str, Any]) -> List[str]:
    path = entry.get("path", "")
    return [p for p in path.split("/") if p]


def classify_session_transcript(filename: str) -> Dict[str, Any]:
    if "cron" in filename.lower():
        return {"type": "cron", "sessionKey": filename}
    if ".compaction" in filename:
        return {"type": "compaction", "sessionKey": filename}
    if ".bak" in filename or ".deleted" in filename or ".reset" in filename:
        return {"type": "archive", "sessionKey": filename}
    return {"type": "active", "sessionKey": filename}


def is_cron_run_transcript(filename: str) -> bool:
    return "cron" in filename.lower()


def is_dreaming_narrative_transcript(filename: str) -> bool:
    return "dream" in filename.lower() or "narrative" in filename.lower()


def parse_session_file_entry(entry: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "sessionKey": entry.get("sessionKey", ""),
        "filePath": entry.get("filePath", ""),
        "fileSize": entry.get("fileSize", 0),
        "lastModified": entry.get("lastModified", 0),
        "classification": classify_session_transcript(entry.get("sessionKey", "")),
    }
