"""Ordered Gateway startup task runner.

Mirrors src/gateway/startup-tasks.ts.
"""

from __future__ import annotations

from typing import Any

StartupTask = Any

async def run_startup_tasks(*args: Any, **kwargs: Any) -> Any: ...
