"""Built-in OpenClaw harness registration.

Harness selection uses this factory to expose the embedded OpenClaw runtime
through the same AgentHarness contract as external harness plugins.

The actual embedded attempt runner is resolved lazily; this stub returns a
harness whose ``runAttempt`` delegates to the embedded runner when available.
"""

from __future__ import annotations

from typing import Any


def _openclaw_embedded_context_engine_host_capabilities() -> list[str]:
    try:
        from openclaw.context_engine.host_compat import OPENCLAW_EMBEDDED_CONTEXT_ENGINE_HOST

        return list(OPENCLAW_EMBEDDED_CONTEXT_ENGINE_HOST.get("capabilities", []))
    except Exception:
        return []


async def _run_embedded_attempt(params: dict[str, Any]) -> dict[str, Any]:
    from openclaw.agents.embedded_agent_runner.run.attempt import run_embedded_attempt

    return await run_embedded_attempt(params)


def create_openclaw_agent_harness() -> Any:
    """Create the built-in harness backed by the embedded OpenClaw agent runner."""

    class _OpenClawHarness:
        id = "openclaw"
        label = "OpenClaw embedded agent"
        contextEngineHostCapabilities = _openclaw_embedded_context_engine_host_capabilities()

        def supports(self, ctx: dict[str, Any]) -> dict[str, Any]:
            return {"supported": True, "priority": 0}

        async def run_attempt(self, params: dict[str, Any]) -> dict[str, Any]:
            return await _run_embedded_attempt(params)

    return _OpenClawHarness()
