"""Mirrors src/channels/mention-gating.ts."""

from __future__ import annotations

from typing import Any

MentionGateParams = Any
MentionGateResult = Any
MentionGateWithBypassParams = Any
MentionGateWithBypassResult = Any
InboundImplicitMentionKind = Any
InboundMentionFacts = Any
InboundMentionPolicy = Any
ResolveInboundMentionDecisionFlatParams = Any
ResolveInboundMentionDecisionNestedParams = Any
ResolveInboundMentionDecisionParams = Any
InboundMentionDecision = Any

def implicit_mention_kind_when(*args: Any, **kwargs: Any) -> Any: ...
def resolve_inbound_mention_decision(*args: Any, **kwargs: Any) -> Any: ...
def resolve_mention_gating(*args: Any, **kwargs: Any) -> Any: ...
def resolve_mention_gating_with_bypass(*args: Any, **kwargs: Any) -> Any: ...
