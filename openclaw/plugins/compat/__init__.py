"""Plugin compatibility types and registry."""

from .registry import (
    PLUGIN_COMPAT_RECORDS,
    get_plugin_compat_record,
    is_plugin_compat_code,
    list_deprecated_plugin_compat_records,
    list_plugin_compat_records,
)
from .types import PluginCompatOwner, PluginCompatRecord, PluginCompatStatus

__all__ = [
    "PLUGIN_COMPAT_RECORDS",
    "PluginCompatOwner",
    "PluginCompatRecord",
    "PluginCompatStatus",
    "get_plugin_compat_record",
    "is_plugin_compat_code",
    "list_deprecated_plugin_compat_records",
    "list_plugin_compat_records",
]
