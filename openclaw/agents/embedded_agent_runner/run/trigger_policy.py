"""Resolves trigger-specific prompt injection behavior."""

from __future__ import annotations

from openclaw.agents.embedded_agent_runner.run.params import EmbeddedRunTrigger

_EMBEDDED_RUN_TRIGGER_POLICY: dict[EmbeddedRunTrigger, dict[str, bool]] = {
    "heartbeat": {"injectHeartbeatPrompt": True},
}


def should_inject_heartbeat_prompt_for_trigger(trigger: EmbeddedRunTrigger | None = None) -> bool:
    if trigger and trigger in _EMBEDDED_RUN_TRIGGER_POLICY:
        return _EMBEDDED_RUN_TRIGGER_POLICY[trigger].get("injectHeartbeatPrompt", False)
    return False