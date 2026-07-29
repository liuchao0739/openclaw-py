"""Inputs for the reusable direct/group/mention gate shared by channel plugins.

Mirrors src/channels/ack-reactions.ts.
"""

from __future__ import annotations

from typing import Any

AckReactionScope = Any
WhatsAppAckReactionMode = Any
AckReactionHandle = Any
AckReactionGateParams = Any

def should_ack_reaction(*args: Any, **kwargs: Any) -> Any: ...
def should_ack_reaction_for_whats_app(*args: Any, **kwargs: Any) -> Any: ...
def create_ack_reaction_handle(*args: Any, **kwargs: Any) -> Any: ...
def remove_ack_reaction_after_reply(*args: Any, **kwargs: Any) -> Any: ...
def remove_ack_reaction_handle_after_reply(*args: Any, **kwargs: Any) -> Any: ...
