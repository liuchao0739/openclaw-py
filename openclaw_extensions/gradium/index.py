"""Gradium plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.gradium.speech_provider import build_gradium_speech_provider


def _register(api: OpenClawPluginApi) -> None:
    api.register_speech_provider(build_gradium_speech_provider())  # type: ignore[attr-defined]


default = define_plugin_entry(
    id="gradium",
    name="Gradium Speech",
    description="Bundled Gradium speech provider",
    register=_register,
)
