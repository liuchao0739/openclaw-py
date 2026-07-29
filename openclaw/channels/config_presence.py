"""Channel configuration presence detection.

Mirrors src/channels/config-presence.ts.
"""

from __future__ import annotations

from typing import Any

ChannelPresenceSignalSource = Any

def has_meaningful_channel_config(*args: Any, **kwargs: Any) -> Any: ...
def list_explicitly_disabled_channel_ids_for_config(*args: Any, **kwargs: Any) -> Any: ...
def list_potential_configured_channel_ids(*args: Any, **kwargs: Any) -> Any: ...
def list_potential_configured_channel_presence_signals(*args: Any, **kwargs: Any) -> Any: ...
