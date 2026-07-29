"""Shared text-control command authorization policy for channel runtimes.

Mirrors src/channels/command-gating.ts.
"""

from __future__ import annotations

from typing import Any

CommandAuthorizer = Any
CommandGatingModeWhenAccessGroupsOff = Any

def resolve_command_authorized_from_authorizers(*args: Any, **kwargs: Any) -> Any: ...
def resolve_control_command_gate(*args: Any, **kwargs: Any) -> Any: ...
def resolve_dual_text_control_command_gate(*args: Any, **kwargs: Any) -> Any: ...
