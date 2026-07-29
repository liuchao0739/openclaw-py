"""Gateway channel plugin reload targeting.

Mirrors src/gateway/plugin-channel-reload-targets.ts.
"""

from __future__ import annotations

from typing import Any

ChannelPluginReloadTarget = Any

def list_channel_plugin_config_target_ids(*args: Any, **kwargs: Any) -> Any: ...
def plugin_config_targets_changed(*args: Any, **kwargs: Any) -> Any: ...
