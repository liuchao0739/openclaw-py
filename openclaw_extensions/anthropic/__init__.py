from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.plugin_entry import define_plugin_entry

from .register_runtime import register_anthropic_plugin


def _register(api: Any) -> None:
    register_anthropic_plugin(api)


default = define_plugin_entry(
    id="anthropic",
    name="Anthropic Provider",
    description="Bundled Anthropic provider plugin",
    register=_register,
)