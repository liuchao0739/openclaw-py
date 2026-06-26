"""Format-time package — duration formatting helpers."""

from .format_duration import (
    format_duration_seconds,
    format_duration_precise,
    format_duration_compact,
    format_duration_human,
)

__all__ = [
    "format_duration_seconds",
    "format_duration_precise",
    "format_duration_compact",
    "format_duration_human",
]
