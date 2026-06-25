"""Channel message capabilities advertised through plugin discovery hooks."""

from __future__ import annotations

from typing import Literal

CHANNEL_MESSAGE_CAPABILITIES = ("presentation", "delivery-pin")
ChannelMessageCapability = Literal["presentation", "delivery-pin"]
