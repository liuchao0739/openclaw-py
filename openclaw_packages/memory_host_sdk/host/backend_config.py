from __future__ import annotations

from typing import Any, List, Optional

from .config_utils import (
    CANONICAL_ROOT_MEMORY_FILENAME,
    normalize_agent_id,
    parse_duration_ms,
    resolve_agent_workspace_dir,
    resolve_user_path,
)
from .fs_utils import is_path_inside
from .string_utils import (
    normalize_lowercase_string_or_empty,
    normalize_string_entries,
    unique_strings,
)


def _escape_qmd_exact_file_pattern(file_name: str) -> str:
    import re
    return re.sub(r'[\\*?[\]{}()!+@]', lambda m: '\\' + m.group(), file_name)


def _resolve_qmd_command(raw_command: str) -> str:
    parsed = raw_command.strip().split()
    return parsed[0] if parsed else "qmd"


DEFAULT_BACKEND = "builtin"
DEFAULT_CITATIONS = "auto"
DEFAULT_QMD_INTERVAL = "5m"
DEFAULT_QMD_DEBOUNCE_MS = 15_000
DEFAULT_QMD_TIMEOUT_MS = 4_000
DEFAULT_QMD_SEARCH_MODE = "search"
DEFAULT_QMD_STARTUP = "off"
DEFAULT_QMD_STARTUP_DELAY_MS = 120_000
DEFAULT_QMD_EMBED_INTERVAL = "60m"
DEFAULT_QMD_COMMAND_TIMEOUT_MS = 30_000
DEFAULT_QMD_UPDATE_TIMEOUT_MS = 120_000
DEFAULT_QMD_EMBED_TIMEOUT_MS = 120_000

DEFAULT_QMD_LIMITS = {
    "maxResults": 4,
    "maxSnippetChars": 450,
    "maxInjectedChars": 2_200,
    "timeoutMs": DEFAULT_QMD_TIMEOUT_MS,
}

DEFAULT_QMD_MCPORTER = {
    "enabled": False,
    "serverName": "qmd",
    "startDaemon": True,
}

DEFAULT_QMD_SCOPE = {
    "default": "deny",
    "rules": [
        {
            "action": "allow",
            "match": {"chatType": "direct"},
        },
    ],
}


def _sanitize_name(input_str: str) -> str:
    lower = normalize_lowercase_string_or_empty(input_str)
    import re
    cleaned = re.sub(r'[^a-z0-9-]+', '-', lower)
    cleaned = re.sub(r'^-+|-+$', '', cleaned)
    return cleaned or "collection"


def _scope_collection_base(base: str, agent_id: str) -> str:
    return f"{base}-{_sanitize_name(agent_id)}"


def _resolve_positive_integer_config(raw: Optional[float], fallback: Optional[float] = None) -> Optional[int]:
    if not isinstance(raw, (int, float)) or raw <= 0:
        return fallback
    return max(1, int(raw))


def _resolve_interval_ms(raw: Optional[str]) -> int:
    value = (raw or "").strip()
    if not value:
        return parse_duration_ms(DEFAULT_QMD_INTERVAL, {"defaultUnit": "m"})
    try:
        return parse_duration_ms(value, {"defaultUnit": "m"})
    except Exception:
        return parse_duration_ms(DEFAULT_QMD_INTERVAL, {"defaultUnit": "m"})


def _resolve_debounce_ms(raw: Optional[float]) -> int:
    if isinstance(raw, (int, float)) and raw == raw and raw >= 0:
        return int(raw)
    return DEFAULT_QMD_DEBOUNCE_MS


def _resolve_timeout_ms(raw: Optional[float], fallback: float) -> int:
    result = _resolve_positive_integer_config(raw, fallback)
    return result if result is not None else int(fallback)


def _resolve_startup_mode(raw: Optional[str]) -> str:
    if raw in ("idle", "immediate", "off"):
        return raw
    return DEFAULT_QMD_STARTUP


def _resolve_startup_delay_ms(raw: Optional[float]) -> int:
    if isinstance(raw, (int, float)) and raw == raw and raw >= 0:
        return int(raw)
    return DEFAULT_QMD_STARTUP_DELAY_MS


def _resolve_search_mode(raw: Optional[str]) -> str:
    if raw in ("search", "vsearch", "query"):
        return raw
    return DEFAULT_QMD_SEARCH_MODE


def _resolve_limits(raw: Optional[dict]) -> dict:
    return {
        "maxResults": _resolve_positive_integer_config(raw.get("maxResults") if raw else None, DEFAULT_QMD_LIMITS["maxResults"]) or DEFAULT_QMD_LIMITS["maxResults"],
        "maxSnippetChars": _resolve_positive_integer_config(raw.get("maxSnippetChars") if raw else None, DEFAULT_QMD_LIMITS["maxSnippetChars"]) or DEFAULT_QMD_LIMITS["maxSnippetChars"],
        "maxInjectedChars": _resolve_positive_integer_config(raw.get("maxInjectedChars") if raw else None, DEFAULT_QMD_LIMITS["maxInjectedChars"]) or DEFAULT_QMD_LIMITS["maxInjectedChars"],
        "timeoutMs": _resolve_positive_integer_config(raw.get("timeoutMs") if raw else None, DEFAULT_QMD_LIMITS["timeoutMs"]) or DEFAULT_QMD_LIMITS["timeoutMs"],
    }


def _resolve_mcporter_config(raw: Optional[dict]) -> dict:
    parsed = dict(DEFAULT_QMD_MCPORTER)
    if not raw:
        return parsed
    if "enabled" in raw:
        parsed["enabled"] = raw["enabled"]
    if isinstance(raw.get("serverName"), str) and raw["serverName"].strip():
        parsed["serverName"] = raw["serverName"].strip()
    if "startDaemon" in raw:
        parsed["startDaemon"] = raw["startDaemon"]
    if parsed["enabled"] and "startDaemon" not in raw:
        parsed["startDaemon"] = True
    return parsed


def resolve_memory_backend_config(cfg: dict, agent_id: str) -> dict:
    normalized_agent_id = normalize_agent_id(agent_id)
    backend = (cfg.get("memory", {}) or {}).get("backend", DEFAULT_BACKEND)
    citations = (cfg.get("memory", {}) or {}).get("citations", DEFAULT_CITATIONS)

    if backend != "qmd":
        return {"backend": "builtin", "citations": citations}

    workspace_dir = resolve_agent_workspace_dir(cfg, normalized_agent_id)
    qmd_cfg = (cfg.get("memory", {}) or {}).get("qmd", {})
    include_default_memory = qmd_cfg.get("includeDefaultMemory", True)
    name_set: set = set()

    agent_entry = None
    agents = cfg.get("agents", {}).get("list", [])
    if isinstance(agents, list):
        for entry in agents:
            if entry and normalize_agent_id(entry.get("id")) == normalized_agent_id:
                agent_entry = entry
                break

    merged_extra_paths = normalize_string_entries(
        [
            *(cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}).get("extraPaths", []) or []),
            *(agent_entry.get("memorySearch", {}).get("extraPaths", []) if agent_entry else []),
        ]
    )
    deduped_extra_paths = unique_strings(merged_extra_paths)

    merged_extra_collections = [
        *(cfg.get("agents", {}).get("defaults", {}).get("memorySearch", {}).get("qmd", {}).get("extraCollections", []) or []),
        *(agent_entry.get("memorySearch", {}).get("qmd", {}).get("extraCollections", []) if agent_entry else []),
    ]

    all_qmd_paths = [
        *(qmd_cfg.get("paths", []) or []),
        *[{"path": p} for p in deduped_extra_paths],
        *merged_extra_collections,
    ]

    collections = []

    if include_default_memory:
        entries = [
            {"path": workspace_dir, "pattern": CANONICAL_ROOT_MEMORY_FILENAME, "base": "memory-root"},
            {"path": os.path.join(workspace_dir, "memory"), "pattern": "**/*.md", "base": "memory-dir"},
        ]
        for entry in entries:
            name = _sanitize_name(_scope_collection_base(entry["base"], normalized_agent_id))
            if name not in name_set:
                name_set.add(name)
            else:
                suffix = 2
                while f"{name}-{suffix}" in name_set:
                    suffix += 1
                name = f"{name}-{suffix}"
                name_set.add(name)
            collections.append({"name": name, "path": entry["path"], "pattern": entry["pattern"], "kind": "memory"})

    for idx, entry in enumerate(all_qmd_paths):
        if not isinstance(entry, dict):
            continue
        path_val = (entry.get("path") or "").strip()
        if not path_val:
            continue
        resolved = resolve_user_path(path_val) if path_val.startswith("~") or os.path.isabs(path_val) else os.path.abspath(os.path.join(workspace_dir, path_val))
        pattern = (entry.get("pattern") or "**/*.md").strip()
        try:
            stat = os.stat(resolved)
            import stat as stat_module
            if stat_module.S_ISREG(stat.st_mode):
                resolved = os.path.dirname(resolved)
                pattern = _escape_qmd_exact_file_pattern(os.path.basename(resolved))
        except OSError:
            pass
        name = _sanitize_name(_scope_collection_base(entry.get("name") or f"custom-{idx + 1}", normalized_agent_id))
        if name not in name_set:
            name_set.add(name)
        else:
            suffix = 2
            while f"{name}-{suffix}" in name_set:
                suffix += 1
            name = f"{name}-{suffix}"
            name_set.add(name)
        collections.append({"name": name, "path": resolved, "pattern": pattern, "kind": "custom"})

    raw_command = (qmd_cfg.get("command") or "qmd").strip()
    command = _resolve_qmd_command(raw_command)

    resolved = {
        "command": command,
        "mcporter": _resolve_mcporter_config(qmd_cfg.get("mcporter")),
        "searchMode": _resolve_search_mode(qmd_cfg.get("searchMode")),
        "rerank": qmd_cfg.get("rerank"),
        "searchTool": qmd_cfg.get("searchTool"),
        "collections": collections,
        "includeDefaultMemory": include_default_memory,
        "sessions": {
            "enabled": bool((qmd_cfg.get("sessions") or {}).get("enabled")),
            "exportDir": (qmd_cfg.get("sessions") or {}).get("exportDir"),
            "retentionDays": _resolve_positive_integer_config((qmd_cfg.get("sessions") or {}).get("retentionDays")),
        },
        "update": {
            "intervalMs": _resolve_interval_ms((qmd_cfg.get("update") or {}).get("interval")),
            "debounceMs": _resolve_debounce_ms((qmd_cfg.get("update") or {}).get("debounceMs")),
            "onBoot": (qmd_cfg.get("update") or {}).get("onBoot", True),
            "startup": _resolve_startup_mode((qmd_cfg.get("update") or {}).get("startup")),
            "startupDelayMs": _resolve_startup_delay_ms((qmd_cfg.get("update") or {}).get("startupDelayMs")),
            "waitForBootSync": (qmd_cfg.get("update") or {}).get("waitForBootSync", False),
            "embedIntervalMs": _resolve_interval_ms((qmd_cfg.get("update") or {}).get("embedInterval")),
            "commandTimeoutMs": _resolve_timeout_ms((qmd_cfg.get("update") or {}).get("commandTimeoutMs"), DEFAULT_QMD_COMMAND_TIMEOUT_MS),
            "updateTimeoutMs": _resolve_timeout_ms((qmd_cfg.get("update") or {}).get("updateTimeoutMs"), DEFAULT_QMD_UPDATE_TIMEOUT_MS),
            "embedTimeoutMs": _resolve_timeout_ms((qmd_cfg.get("update") or {}).get("embedTimeoutMs"), DEFAULT_QMD_EMBED_TIMEOUT_MS),
        },
        "limits": _resolve_limits(qmd_cfg.get("limits")),
        "scope": qmd_cfg.get("scope", DEFAULT_QMD_SCOPE),
    }

    return {"backend": "qmd", "citations": citations, "qmd": resolved}
