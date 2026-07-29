"""Cached lookup view for active channel plugin registry entries and aliases.

Mirrors src/channels/registry-lookup.ts.
"""

from __future__ import annotations

from typing import Any

def list_registered_channel_plugin_entries(*args: Any, **kwargs: Any) -> Any: ...
def find_registered_channel_plugin_entry(*args: Any, **kwargs: Any) -> Any: ...
def find_registered_channel_plugin_entry_by_id(*args: Any, **kwargs: Any) -> Any: ...
