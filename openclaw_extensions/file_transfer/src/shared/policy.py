from __future__ import annotations

import os
import fnmatch
from typing import Any, Literal, TypedDict


FilePolicyKind = Literal["read", "write"]
FilePolicyAskMode = Literal["off", "on-miss", "always"]


class FilePolicyDecisionAllow(TypedDict):
    ok: Literal[True]
    reason: Literal["matched-allow"]
    maxBytes: int | None
    followSymlinks: bool


class FilePolicyDecisionAskAlways(TypedDict):
    ok: Literal[True]
    reason: Literal["ask-always"]
    askMode: FilePolicyAskMode
    maxBytes: int | None
    followSymlinks: bool


class FilePolicyDecisionDeny(TypedDict, total=False):
    ok: Literal[False]
    code: Literal["NO_POLICY", "POLICY_DENIED"]
    reason: str
    askable: bool
    askMode: FilePolicyAskMode
    maxBytes: int | None
    followSymlinks: bool


FilePolicyDecision = FilePolicyDecisionAllow | FilePolicyDecisionAskAlways | FilePolicyDecisionDeny


class NodeFilePolicyConfig(TypedDict, total=False):
    ask: FilePolicyAskMode
    allowReadPaths: list[str]
    allowWritePaths: list[str]
    denyPaths: list[str]
    maxBytes: int
    followSymlinks: bool


FilePolicyConfig = dict[str, NodeFilePolicyConfig]


def _as_file_policy_config(value: Any) -> FilePolicyConfig | None:
    if not value or not isinstance(value, dict):
        return None
    return value


def _read_file_policy_config_from_plugin_config(plugin_config: Any) -> FilePolicyConfig | None:
    if not plugin_config or not isinstance(plugin_config, dict):
        return None
    nodes = plugin_config.get("nodes")
    return _as_file_policy_config(nodes)


def _read_plugin_config_from_runtime_config() -> dict[str, Any] | None:
    from openclaw.plugin_sdk.runtime_config_snapshot import get_runtime_config

    cfg = get_runtime_config()
    if not isinstance(cfg, dict):
        return None
    plugins = cfg.get("plugins")
    if not isinstance(plugins, dict):
        return None
    entries = plugins.get("entries")
    if not isinstance(entries, dict):
        return None
    entry = entries.get("file-transfer")
    if not isinstance(entry, dict):
        return None
    plugin_config = entry.get("config")
    if plugin_config and isinstance(plugin_config, dict):
        return plugin_config
    return None


def _read_file_policy_config(plugin_config: dict[str, Any] | None = None) -> FilePolicyConfig | None:
    config_from_runtime = _read_file_policy_config_from_plugin_config(
        _read_plugin_config_from_runtime_config()
    )
    if config_from_runtime is not None:
        return config_from_runtime
    if plugin_config is not None:
        return _read_file_policy_config_from_plugin_config(plugin_config)
    return None


def _expand_tilde(p: str) -> str:
    if p.startswith("~/") or p == "~":
        return os.path.join(os.path.expanduser("~"), p[1:] if p != "~" else "")
    return p


def _normalize_globs(patterns: list[str] | None) -> list[str]:
    if patterns is None:
        return []
    result = []
    for p in patterns:
        if isinstance(p, str) and p.strip():
            result.append(_expand_tilde(p.strip()))
    return result


def _matches_any(target: str, patterns: list[str]) -> bool:
    normalized_target = target.replace("\\", "/")
    for pattern in patterns:
        normalized_pattern = pattern.replace("\\", "/")
        if fnmatch.fnmatch(target, pattern) or fnmatch.fnmatch(normalized_target, normalized_pattern):
            return True
    return False


def _resolve_node_policy(
    config: FilePolicyConfig,
    node_id: str,
    node_display_name: str | None = None,
) -> tuple[str, NodeFilePolicyConfig] | None:
    candidates = [node_id, node_display_name]
    for key in candidates:
        if key and key in config:
            return (key, config[key])
    if "*" in config:
        return ("*", config["*"])
    return None


def _normalize_ask_mode(value: Any) -> FilePolicyAskMode:
    if value in ("on-miss", "always", "off"):
        return value
    return "off"


def _contains_parent_ref_segment(p: str) -> bool:
    unified = p.replace("\\", "/")
    parts = unified.split("/")
    return ".." in parts


def evaluate_file_policy(
    node_id: str,
    kind: FilePolicyKind,
    path: str,
    node_display_name: str | None = None,
    plugin_config: dict[str, Any] | None = None,
) -> FilePolicyDecision:
    if _contains_parent_ref_segment(path):
        return {
            "ok": False,
            "code": "POLICY_DENIED",
            "reason": "path contains '..' segments; reject before glob match",
            "askable": False,
        }

    config = _read_file_policy_config(plugin_config)
    if config is None:
        return {
            "ok": False,
            "code": "NO_POLICY",
            "reason": "no plugins.entries.file-transfer.config.nodes config; file-transfer is deny-by-default until configured",
            "askable": False,
        }

    resolved = _resolve_node_policy(config, node_id, node_display_name)
    if resolved is None:
        display = node_display_name or node_id
        return {
            "ok": False,
            "code": "NO_POLICY",
            "reason": f'no file-transfer policy entry for "{display}"; configure plugins.entries.file-transfer.config.nodes or "*"',
            "askable": False,
        }

    _key, node_config = resolved
    ask_mode = _normalize_ask_mode(node_config.get("ask"))

    max_bytes_val = node_config.get("maxBytes")
    if isinstance(max_bytes_val, (int, float)) and max_bytes_val == max_bytes_val and max_bytes_val >= 1:
        max_bytes = int(max_bytes_val)
    else:
        max_bytes = None

    follow_symlinks = node_config.get("followSymlinks", False) is True

    deny_patterns = _normalize_globs(node_config.get("denyPaths"))
    if _matches_any(path, deny_patterns):
        return {
            "ok": False,
            "code": "POLICY_DENIED",
            "reason": "path matches a denyPaths pattern",
            "askable": False,
            "askMode": ask_mode,
            "maxBytes": max_bytes,
            "followSymlinks": follow_symlinks,
        }

    if ask_mode == "always":
        return {
            "ok": True,
            "reason": "ask-always",
            "askMode": ask_mode,
            "maxBytes": max_bytes,
            "followSymlinks": follow_symlinks,
        }

    if kind == "read":
        allow_patterns = _normalize_globs(node_config.get("allowReadPaths"))
    else:
        allow_patterns = _normalize_globs(node_config.get("allowWritePaths"))

    if allow_patterns and _matches_any(path, allow_patterns):
        return {
            "ok": True,
            "reason": "matched-allow",
            "maxBytes": max_bytes,
            "followSymlinks": follow_symlinks,
        }

    if ask_mode == "on-miss":
        kind_label = "Read" if kind == "read" else "Write"
        return {
            "ok": False,
            "code": "POLICY_DENIED",
            "reason": f"path does not match any allow{kind_label}Paths pattern",
            "askable": True,
            "askMode": ask_mode,
            "maxBytes": max_bytes,
            "followSymlinks": follow_symlinks,
        }

    kind_label = "Read" if kind == "read" else "Write"
    if not allow_patterns:
        reason = f"no allow{kind_label}Paths configured"
    else:
        reason = f"path does not match any allow{kind_label}Paths pattern"
    return {
        "ok": False,
        "code": "POLICY_DENIED",
        "reason": reason,
        "askable": False,
        "askMode": ask_mode,
        "maxBytes": max_bytes,
        "followSymlinks": follow_symlinks,
    }


def _assert_safe_config_key(key: str) -> str:
    if key in ("__proto__", "prototype", "constructor"):
        raise ValueError(f"refusing to persist file-transfer policy under unsafe key: {key}")
    return key


async def persist_allow_always(
    node_id: str,
    kind: FilePolicyKind,
    path: str,
    node_display_name: str | None = None,
) -> None:
    from openclaw.plugin_sdk.config_mutation import mutate_config_file

    field = "allowReadPaths" if kind == "read" else "allowWritePaths"

    async def _mutate(draft: dict[str, Any]) -> None:
        plugins = draft.setdefault("plugins", {})
        entries = plugins.setdefault("entries", {})
        plugin_entry = entries.setdefault("file-transfer", {})
        plugin_config = plugin_entry.setdefault("config", {})
        file_transfer = plugin_config.setdefault("nodes", {})

        candidates = [node_id, node_display_name]
        key = None
        for c in candidates:
            if c and c in file_transfer:
                key = c
                break
        if key is None:
            safe_key = _assert_safe_config_key(node_display_name or node_id)
            file_transfer[safe_key] = {}
            key = safe_key

        entry = file_transfer[key]
        list_val = entry.get(field, [])
        if not isinstance(list_val, list):
            list_val = []
        if path not in list_val:
            list_val.append(path)
        entry[field] = list_val

    await mutate_config_file(
        after_write={"mode": "none", "reason": "file-transfer allow-always policy update"},
        mutate=_mutate,
    )