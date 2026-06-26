"""Security package — scan paths, system tags."""

from .scan_paths import extension_uses_skipped_scanner_path
from .system_tags import sanitize_inbound_system_tags

__all__ = [
    "extension_uses_skipped_scanner_path",
    "sanitize_inbound_system_tags",
]
