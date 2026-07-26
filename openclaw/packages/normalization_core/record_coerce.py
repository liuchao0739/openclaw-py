"""Backward-compatible re-export of record coercion helpers."""

from openclaw_packages.normalization_core import record_coerce as _record_coerce

__all__ = list(_record_coerce.__all__)
globals().update({name: getattr(_record_coerce, name) for name in __all__})
