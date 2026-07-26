"""Backward-compatible re-export of normalization_core from openclaw_packages."""

from openclaw_packages import normalization_core as _normalization_core

__all__ = list(_normalization_core.__all__)
globals().update({name: getattr(_normalization_core, name) for name in __all__})
