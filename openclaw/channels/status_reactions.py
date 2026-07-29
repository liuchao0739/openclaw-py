"""Status-reaction controller helpers for channel-visible agent activity.

Mirrors src/channels/status-reactions.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_EMOJIS: Any = None
DEFAULT_TIMING: Any = None
CODING_TOOL_TOKENS: Any = None
WEB_TOOL_TOKENS: Any = None
DEPLOY_TOOL_TOKENS: Any = None
BUILD_TOOL_TOKENS: Any = None
CONCIERGE_TOOL_TOKENS: Any = None

StatusReactionAdapter = Any
StatusReactionEmojis = Any
StatusReactionTiming = Any
StatusReactionController = Any

def resolve_tool_emoji(*args: Any, **kwargs: Any) -> Any: ...
def create_status_reaction_controller(*args: Any, **kwargs: Any) -> Any: ...
