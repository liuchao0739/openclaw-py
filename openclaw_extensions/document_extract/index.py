"""Document Extract plugin entrypoint registers its OpenClaw integration."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry


def _register(_api: OpenClawPluginApi) -> None:
    # Runtime is exposed through document_extractor.py so document hot paths can
    # load only the narrow extractor artifact instead of the full plugin entrypoint.
    return None


default = define_plugin_entry(
    id="document-extract",
    name="Document Extraction",
    description="Extract text and fallback page images from local document attachments.",
    register=_register,
)
