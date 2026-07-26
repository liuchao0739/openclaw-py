"""Azure Speech plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.azure_speech.speech_provider import build_azure_speech_provider


def _register(api: OpenClawPluginApi) -> None:
    api.register_speech_provider(build_azure_speech_provider())  # type: ignore[attr-defined]


default = define_plugin_entry(
    id="azure-speech",
    name="Azure Speech",
    description="Bundled Azure Speech provider",
    register=_register,
)
