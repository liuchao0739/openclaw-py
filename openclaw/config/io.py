from __future__ import annotations

import json
import hashlib
from pathlib import Path
from typing import Any, Callable

from openclaw.config.paths import (
    CONFIG_PATH,
    DEFAULT_GATEWAY_PORT,
    STATE_DIR,
    resolve_config_path,
    resolve_state_dir,
)
from openclaw.config.models import OpenClawConfig
from openclaw.config.mutation_conflict import ConfigMutationConflictError


def hash_config_raw(raw: str | None) -> str:
    if raw is None:
        return hashlib.sha256(b"null").hexdigest()
    return hashlib.sha256(raw.encode("utf-8")).hexdigest()


def parse_config_json5(
    raw: str,
    json5: Any = None,
) -> dict[str, Any]:
    try:
        return json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        pass
    if json5 is not None:
        try:
            return json5.parse(raw)
        except Exception:
            pass
    raise ValueError(f"Failed to parse config: {raw[:100]}")


class ConfigRuntimeRefreshError(Exception):
    def __init__(self, message: str, cause: Any = None):
        super().__init__(message)
        self.name = "ConfigRuntimeRefreshError"
        self.cause = cause


class ConfigIO:
    def __init__(
        self,
        env: dict[str, str] | None = None,
        config_path: str | None = None,
    ):
        self._env = env
        self._config_path = config_path
        self._runtime_snapshot: dict[str, Any] | None = None
        self._runtime_source_snapshot: dict[str, Any] | None = None
        self._listeners: list[Callable] = []

    @property
    def config_path(self) -> str:
        if self._config_path:
            return self._config_path
        return resolve_config_path(self._env)

    def get_runtime_config(self) -> OpenClawConfig:
        if self._runtime_snapshot:
            return OpenClawConfig.model_validate(self._runtime_snapshot)
        return self.load_config()

    def get_runtime_config_snapshot(self) -> dict[str, Any] | None:
        return self._runtime_snapshot

    def get_runtime_config_source_snapshot(self) -> dict[str, Any] | None:
        return self._runtime_source_snapshot

    def set_runtime_config_snapshot(
        self,
        snapshot: dict[str, Any],
        source_snapshot: dict[str, Any] | None = None,
    ) -> None:
        self._runtime_snapshot = snapshot
        self._runtime_source_snapshot = source_snapshot or snapshot

    def clear_runtime_config_snapshot(self) -> None:
        self._runtime_snapshot = None
        self._runtime_source_snapshot = None

    def register_config_write_listener(self, listener: Callable) -> None:
        self._listeners.append(listener)

    def reset_config_runtime_state(self) -> None:
        self.clear_runtime_config_snapshot()
        self._listeners.clear()

    def load_config(self) -> OpenClawConfig:
        path = Path(self.config_path)
        if not path.exists():
            return OpenClawConfig()
        raw = path.read_text(encoding="utf-8")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {}
        return OpenClawConfig.model_validate(parsed)

    def read_config_file_snapshot(self) -> dict[str, Any]:
        path = Path(self.config_path)
        if not path.exists():
            return {
                "path": str(path),
                "exists": False,
                "raw": None,
                "parsed": {},
                "sourceConfig": {},
                "resolved": {},
                "valid": True,
                "runtimeConfig": {},
                "config": {},
                "hash": None,
                "issues": [],
                "warnings": [],
            }
        raw = path.read_text(encoding="utf-8")
        parsed = json.loads(raw)
        return {
            "path": str(path),
            "exists": True,
            "raw": raw,
            "parsed": parsed,
            "sourceConfig": parsed,
            "resolved": parsed,
            "valid": True,
            "runtimeConfig": parsed,
            "config": parsed,
            "hash": hash_config_raw(raw),
            "issues": [],
            "warnings": [],
        }

    def write_config_file(
        self,
        cfg: OpenClawConfig | dict[str, Any],
        options: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        path = Path(self.config_path)
        if isinstance(cfg, OpenClawConfig):
            raw = json.dumps(cfg.model_dump(exclude_none=True), indent=2)
        else:
            raw = json.dumps(cfg, indent=2)
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(raw + "\n", encoding="utf-8")
        for listener in self._listeners:
            try:
                listener({"configPath": str(path), "config": cfg})
            except Exception:
                pass
        return {"persistedHash": hash_config_raw(raw), "persistedConfig": cfg}


def create_config_io(
    overrides: dict[str, Any] | None = None,
) -> ConfigIO:
    return ConfigIO(
        env=(overrides or {}).get("env"),
        config_path=(overrides or {}).get("configPath"),
    )


def load_config(
    env: dict[str, str] | None = None,
    config_path: str | None = None,
) -> OpenClawConfig:
    io = create_config_io({"env": env, "configPath": config_path})
    return io.load_config()


def read_best_effort_config(
    env: dict[str, str] | None = None,
    config_path: str | None = None,
) -> OpenClawConfig:
    return load_config(env, config_path)


def read_best_effort_config_snapshot(
    env: dict[str, str] | None = None,
    config_path: str | None = None,
) -> dict[str, Any]:
    io = create_config_io({"env": env, "configPath": config_path})
    return io.read_config_file_snapshot()


def resolve_config_snapshot_hash(snapshot: dict[str, Any]) -> str | None:
    h = snapshot.get("hash")
    if isinstance(h, str) and h.strip():
        return h.strip()
    raw = snapshot.get("raw")
    if not isinstance(raw, str):
        return None
    return hash_config_raw(raw)
