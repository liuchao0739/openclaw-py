from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ConfigWriteAfterWrite(BaseModel):
    runtime_refresh: bool | None = Field(default=None, alias="runtimeRefresh")
    runtime_refresh_options: dict[str, Any] | None = Field(
        default=None, alias="runtimeRefreshOptions"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class ConfigWriteFollowUp(BaseModel):
    action: str | None = None
    config_path: str | None = Field(default=None, alias="configPath")

    model_config = {"populate_by_name": True, "extra": "allow"}


class RuntimeConfigSnapshotMetadata(BaseModel):
    hash: str | None = None
    path: str | None = None
    written_at: str | None = Field(default=None, alias="writtenAt")

    model_config = {"populate_by_name": True}


_runtime_config_snapshot: dict[str, Any] | None = None
_runtime_config_source_snapshot: dict[str, Any] | None = None
_runtime_config_snapshot_refresh_handler: Any = None
_runtime_config_write_listeners: list[Any] = []
_runtime_config_cache: dict[str, Any] = {}
_last_known_good_config: dict[str, Any] | None = None


def get_runtime_config():
    return _runtime_config_snapshot


def get_runtime_config_snapshot():
    return _runtime_config_snapshot


def get_runtime_config_source_snapshot():
    return _runtime_config_source_snapshot


def get_runtime_config_snapshot_metadata():
    return RuntimeConfigSnapshotMetadata()


def set_runtime_config_snapshot(snapshot: dict[str, Any] | None):
    global _runtime_config_snapshot
    _runtime_config_snapshot = snapshot


def clear_runtime_config_snapshot():
    global _runtime_config_snapshot
    _runtime_config_snapshot = None


def clear_config_cache():
    global _runtime_config_cache
    _runtime_config_cache.clear()


def reset_config_runtime_state():
    global _runtime_config_snapshot, _runtime_config_source_snapshot
    global _runtime_config_write_listeners, _runtime_config_cache
    _runtime_config_snapshot = None
    _runtime_config_source_snapshot = None
    _runtime_config_write_listeners = []
    _runtime_config_cache = {}


def set_runtime_config_snapshot_refresh_handler(handler):
    global _runtime_config_snapshot_refresh_handler
    _runtime_config_snapshot_refresh_handler = handler


def get_runtime_config_snapshot_refresh_handler():
    return _runtime_config_snapshot_refresh_handler


def register_config_write_listener(listener):
    _runtime_config_write_listeners.append(listener)


def notify_runtime_config_write_listeners(notification):
    for listener in _runtime_config_write_listeners:
        try:
            listener(notification)
        except Exception:
            pass


def resolve_runtime_config_cache_key(config_path: str):
    return config_path


def resolve_config_snapshot_hash(snapshot: dict[str, Any] | None) -> str | None:
    if snapshot is None:
        return None
    return snapshot.get("hash")


def hash_runtime_config_value(value: Any) -> str:
    import hashlib
    import json
    serialized = json.dumps(value, sort_keys=True, default=str)
    return hashlib.sha256(serialized.encode()).hexdigest()


def project_config_onto_runtime_source_snapshot(config: dict[str, Any]) -> dict[str, Any]:
    return config


def resolve_config_write_after_write(after_write: ConfigWriteAfterWrite | dict | None):
    if after_write is None:
        return ConfigWriteAfterWrite()
    if isinstance(after_write, dict):
        return ConfigWriteAfterWrite(**after_write)
    return after_write


def resolve_config_write_follow_up(after_write: ConfigWriteAfterWrite | None):
    return ConfigWriteFollowUp()
