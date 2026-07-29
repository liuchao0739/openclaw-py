"""Claude CLI session history importer.

Mirrors src/gateway/cli-session-history.claude.ts.
"""

from __future__ import annotations

from typing import Any

CLAUDE_CLI_PROVIDER: Any = None

ClaudeCliFallbackSeed = Any

def resolve_claude_cli_binding_session_id(*args: Any, **kwargs: Any) -> Any: ...
def resolve_claude_cli_session_file_path(*args: Any, **kwargs: Any) -> Any: ...
def read_claude_cli_session_messages(*args: Any, **kwargs: Any) -> Any: ...
def read_claude_cli_fallback_seed(*args: Any, **kwargs: Any) -> Any: ...
