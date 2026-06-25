"""Channel plugins outbound — presentation limits, interactive, direct text, loader."""

from openclaw.channels.plugins.outbound.direct_text_media import (
    format_direct_text_payload,
    split_text_and_media,
)
from openclaw.channels.plugins.outbound.interactive import (
    build_interactive_presentation,
    is_interactive_presentation,
)
from openclaw.channels.plugins.outbound.load import load_outbound_plugin
from openclaw.channels.plugins.outbound.load_types import (
    ChannelPresentationCapabilities,
    OutboundPluginLoadResult,
)
from openclaw.channels.plugins.outbound.presentation_limits import (
    action_capacity,
    fallback_list_block,
    fits_byte_limit,
    truncate_presentation_text,
    truncate_text,
    truncate_utf8_bytes,
)

__all__ = [
    "ChannelPresentationCapabilities",
    "OutboundPluginLoadResult",
    "action_capacity",
    "build_interactive_presentation",
    "fallback_list_block",
    "fits_byte_limit",
    "format_direct_text_payload",
    "is_interactive_presentation",
    "load_outbound_plugin",
    "split_text_and_media",
    "truncate_presentation_text",
    "truncate_text",
    "truncate_utf8_bytes",
]
