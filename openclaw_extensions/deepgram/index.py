"""Deepgram plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.deepgram.media_understanding_provider import (
    deepgram_media_understanding_provider,
)
from openclaw_extensions.deepgram.realtime_transcription_provider import (
    build_deepgram_realtime_transcription_provider,
)


def _register(api: OpenClawPluginApi) -> None:
    api.register_media_understanding_provider(deepgram_media_understanding_provider)
    api.register_realtime_transcription_provider(  # type: ignore[attr-defined]
        build_deepgram_realtime_transcription_provider()
    )


default = define_plugin_entry(
    id="deepgram",
    name="Deepgram Media Understanding",
    description="Bundled Deepgram audio transcription provider",
    register=_register,
)
