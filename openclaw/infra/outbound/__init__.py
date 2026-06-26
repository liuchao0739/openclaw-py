"""Outbound package — identity types, thread id, abort helpers."""

from .identity_types import OutboundIdentity
from .thread_id import normalize_outbound_thread_id
from .abort import throw_if_aborted

__all__ = [
    "OutboundIdentity",
    "normalize_outbound_thread_id",
    "throw_if_aborted",
]
