"""Hooks package."""

from .gmail_watcher_errors import is_address_in_use_error
from .internal_hook_types import InternalHookEvent
from .legacy_config import get_legacy_internal_hook_handlers
from .installs import record_hook_install, HookInstallUpdate

__all__ = [
    "is_address_in_use_error",
    "InternalHookEvent",
    "get_legacy_internal_hook_handlers",
    "record_hook_install",
    "HookInstallUpdate",
]
