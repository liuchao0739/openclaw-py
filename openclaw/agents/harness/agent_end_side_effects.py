"""Agent-end side effect runner.

Harnesses use this to trigger core research capture and plugin agent_end hooks
either fire-and-forget or awaited during tests/shutdown.
"""

from __future__ import annotations

import asyncio
from typing import Any

from openclaw.agents.harness.lifecycle_hook_helpers import (
    await_agent_harness_agent_end_hook,
    run_agent_harness_agent_end_hook,
)


async def _run_core_agent_end_side_effects(params: dict[str, Any]) -> None:
    try:
        from openclaw.skills.research.autocapture import run_skill_research_auto_capture

        await run_skill_research_auto_capture(
            {
                "event": params["event"],
                "ctx": params["ctx"],
                **({"config": params["ctx"]["config"]} if params["ctx"].get("config") else {}),
            }
        )
    except Exception:
        pass


def run_agent_end_side_effects(params: dict[str, Any]) -> None:
    """Start agent-end side effects without waiting for completion."""
    try:
        loop = asyncio.get_event_loop()
        loop.create_task(_run_core_agent_end_side_effects(params))
    except Exception:
        pass
    run_agent_harness_agent_end_hook(params)


async def await_agent_end_side_effects(params: dict[str, Any]) -> None:
    """Run agent-end side effects and wait for plugin/core completion."""
    await _run_core_agent_end_side_effects(params)
    await await_agent_harness_agent_end_hook(params)
