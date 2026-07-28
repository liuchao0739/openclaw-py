from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable

from openclaw.llm.core import AssistantMessage, Model
from openclaw.llm.event_stream import AssistantMessageEventStream

CompleteSimpleFn = Callable[[Model, Any, Any | None], AssistantMessage]


@dataclass
class AgentCoreRuntimeDeps:
    streamSimple: Callable[..., AssistantMessageEventStream]
    completeSimple: CompleteSimpleFn


@dataclass
class AgentCoreStreamRuntimeDeps:
    streamSimple: Callable[..., AssistantMessageEventStream]


@dataclass
class AgentCoreCompletionRuntimeDeps:
    completeSimple: CompleteSimpleFn


def _missing_dep(name: str) -> Exception:
    return Exception(
        f'@openclaw/agent-core runtime dependency "{name}" is not configured. '
        "Pass an AgentCoreRuntimeDeps instance or a streamFn explicitly."
    )


def resolve_agent_core_stream_fn(
    runtime: AgentCoreStreamRuntimeDeps | None,
    streamFn: Callable[..., AssistantMessageEventStream] | None = None,
) -> Callable[..., AssistantMessageEventStream]:
    if streamFn is not None:
        return streamFn
    if runtime is not None and runtime.streamSimple is not None:
        return runtime.streamSimple
    raise _missing_dep("streamSimple")


def resolve_agent_core_complete_fn(
    runtime: AgentCoreCompletionRuntimeDeps | None,
) -> CompleteSimpleFn:
    if runtime is not None and runtime.completeSimple is not None:
        return runtime.completeSimple
    raise _missing_dep("completeSimple")
