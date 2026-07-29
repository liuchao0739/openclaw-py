"""Run orphan-key session migration at gateway startup.

Mirrors src/gateway/server-startup-session-migration.ts.
"""

from __future__ import annotations

from typing import Any

async def run_startup_session_migration(*args: Any, **kwargs: Any) -> Any: ...
