"""Agent identity metadata that outbound channels can render with a message.

Mirrors src/infra/outbound/identity-types.ts.
"""

from __future__ import annotations

from typing import TypedDict


class OutboundIdentity(TypedDict, total=False):
    name: str
    avatarUrl: str
    emoji: str
    theme: str
