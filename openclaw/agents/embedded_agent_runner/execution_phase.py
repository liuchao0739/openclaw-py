"""Ordered execution milestones reported by the embedded runner."""

from __future__ import annotations

from typing import Literal

EmbeddedAgentExecutionPhase = Literal[
    "runner_entered",
    "workspace",
    "runtime_plugins",
    "before_agent_reply",
    "model_resolution",
    "auth",
    "context_engine",
    "attempt_dispatch",
    "context_assembled",
    "turn_accepted",
    "process_spawned",
    "tool_execution_started",
    "assistant_output_started",
    "model_call_started",
]

_EMBEDDED_AGENT_EXECUTION_PHASE_LABELS: dict[EmbeddedAgentExecutionPhase, str] = {
    "runner_entered": "runner-entered",
    "workspace": "workspace",
    "runtime_plugins": "runtime-plugins",
    "before_agent_reply": "before-agent-reply",
    "model_resolution": "model-resolution",
    "auth": "auth",
    "context_engine": "context-engine",
    "attempt_dispatch": "attempt-dispatch",
    "context_assembled": "context-assembled",
    "turn_accepted": "turn-accepted",
    "process_spawned": "process-spawned",
    "tool_execution_started": "tool-execution-started",
    "assistant_output_started": "assistant-output-started",
    "model_call_started": "model-call-started",
}


def format_embedded_agent_execution_phase(
    phase: EmbeddedAgentExecutionPhase | None = None,
) -> str | None:
    if not phase:
        return None
    return _EMBEDDED_AGENT_EXECUTION_PHASE_LABELS.get(phase)