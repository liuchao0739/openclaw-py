"""Feishu API module exposes the plugin public contract."""

from __future__ import annotations

from importlib import import_module
from typing import Any

_feishu_subagent_hooks_module: Any | None = None


def _load_feishu_subagent_hooks_module() -> Any:
    global _feishu_subagent_hooks_module
    if _feishu_subagent_hooks_module is None:
        _feishu_subagent_hooks_module = import_module(
            "openclaw_extensions.feishu.src.subagent_hooks"
        )
    return _feishu_subagent_hooks_module


def register_feishu_subagent_hooks(api: Any) -> None:
    async def on_subagent_delivery_target(event: Any, _ctx: Any = None) -> Any:
        module = _load_feishu_subagent_hooks_module()
        return module.handle_feishu_subagent_delivery_target(event)

    async def on_subagent_ended(event: Any, _ctx: Any = None) -> None:
        module = _load_feishu_subagent_hooks_module()
        module.handle_feishu_subagent_ended(event)

    api.on("subagent_delivery_target", on_subagent_delivery_target)
    api.on("subagent_ended", on_subagent_ended)


__all__ = ["register_feishu_subagent_hooks"]
