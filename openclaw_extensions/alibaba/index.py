"""Alibaba Model Studio plugin entry registers the DashScope-backed video provider."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.alibaba.video_generation_provider import (
    build_alibaba_video_generation_provider,
)


def _register(api: OpenClawPluginApi) -> None:
    api.register_video_generation_provider(build_alibaba_video_generation_provider())


default = define_plugin_entry(
    id="alibaba",
    name="Alibaba Model Studio Plugin",
    description="Bundled Alibaba Model Studio video provider plugin",
    register=_register,
)
