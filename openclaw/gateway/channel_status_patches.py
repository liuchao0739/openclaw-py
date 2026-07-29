"""Channel status patch factories centralize timestamp fields that multiple

Mirrors src/gateway/channel-status-patches.ts.
"""

from __future__ import annotations

from typing import Any

ConnectedChannelStatusPatch = Any
TransportActivityChannelStatusPatch = Any

def create_connected_channel_status_patch(*args: Any, **kwargs: Any) -> Any: ...
def create_transport_activity_status_patch(*args: Any, **kwargs: Any) -> Any: ...
