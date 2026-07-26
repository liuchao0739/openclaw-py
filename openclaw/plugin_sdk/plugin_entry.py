"""Plugin entry contracts define the manifest-facing hooks implemented by plugin packages."""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field
from typing import Any, Protocol

from openclaw.plugin_sdk.lazy_value import create_cached_lazy_value_getter

__all__ = [
    "OpenClawPluginApi",
    "OpenClawPluginHttpRouteHandler",
    "PluginLogger",
    "define_plugin_entry",
    "empty_plugin_config_schema",
]


class PluginLogger(Protocol):
    """Logger passed into plugin registration, services, and CLI surfaces."""

    def debug(self, message: str) -> None: ...

    def info(self, message: str) -> None: ...

    def warn(self, message: str) -> None: ...

    def error(self, message: str) -> None: ...


class OpenClawPluginHttpRouteHandler(Protocol):
    """HTTP route handler injected into plugin registration."""

    def __call__(
        self,
        req: Any,
        res: Any,
    ) -> bool | None: ...


class OpenClawPluginApi(Protocol):
    """Main registration API injected into native plugin entry files."""

    def register_http_route(self, params: Mapping[str, Any]) -> None: ...


def _config_error(message: str) -> dict[str, Any]:
    return {"success": False, "error": {"issues": [{"path": [], "message": message}]}}


def empty_plugin_config_schema() -> dict[str, Any]:
    """Return a schema for plugins that intentionally accept no config keys."""

    def safe_parse(value: Any) -> dict[str, Any]:
        if value is None:
            return {"success": True, "data": None}
        if not isinstance(value, dict):
            return _config_error("expected config object")
        if value:
            return _config_error("config must be empty")
        return {"success": True, "data": value}

    return {
        "safeParse": safe_parse,
        "jsonSchema": {
            "type": "object",
            "additionalProperties": False,
            "properties": {},
        },
    }


@dataclass
class DefinedPluginEntry:
    """Normalized object shape that OpenClaw loads from a plugin entry module."""

    id: str
    name: str
    description: str
    register: Callable[[OpenClawPluginApi], None]
    _get_config_schema: Callable[[], Any] = field(repr=False)
    kind: str | None = None
    reload: Any | None = None
    node_host_commands: Any | None = None
    security_audit_collectors: Any | None = None

    @property
    def config_schema(self) -> Any:
        return self._get_config_schema()


def define_plugin_entry(
    *,
    id: str,
    name: str,
    description: str,
    register: Callable[[OpenClawPluginApi], None],
    kind: str | None = None,
    config_schema: Any | Callable[[], Any] | None = None,
    reload: Any | None = None,
    node_host_commands: Any | None = None,
    security_audit_collectors: Any | None = None,
) -> DefinedPluginEntry:
    """Canonical entry helper for non-channel plugins."""
    get_config_schema = create_cached_lazy_value_getter(
        config_schema if config_schema is not None else empty_plugin_config_schema
    )
    return DefinedPluginEntry(
        id=id,
        name=name,
        description=description,
        register=register,
        _get_config_schema=get_config_schema,
        **{
            key: value
            for key, value in (
                ("kind", kind),
                ("reload", reload),
                ("node_host_commands", node_host_commands),
                ("security_audit_collectors", security_audit_collectors),
            )
            if value is not None
        },
    )
