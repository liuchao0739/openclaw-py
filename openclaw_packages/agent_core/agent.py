from __future__ import annotations

import asyncio
import time
from typing import Any, Callable

from openclaw.llm.core import ImageContent, Message, Model, TextContent

from .agent_loop import run_agent_loop, run_agent_loop_continue
from .agent_types import (
    AfterToolCallContext,
    AfterToolCallResult,
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentLoopTurnUpdate,
    AgentMessage,
    AgentState,
    AgentTool,
    BeforeToolCallContext,
    BeforeToolCallResult,
    QueueMode,
    ThinkingLevel,
)
from .reasoning import resolve_agent_reasoning_option
from .runtime_deps import (
    AgentCoreStreamRuntimeDeps,
    resolve_agent_core_stream_fn,
)

__all__ = ["Agent", "QueueMode"]


def _default_convert_to_llm(messages: list[AgentMessage]) -> list[Message]:
    return [
        m
        for m in messages
        if getattr(m, "role", None) in ("user", "assistant", "toolResult")
    ]


EMPTY_USAGE = {
    "input": 0,
    "output": 0,
    "cacheRead": 0,
    "cacheWrite": 0,
    "totalTokens": 0,
    "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
}

DEFAULT_MODEL: Model = Model(
    id="unknown",
    name="unknown",
    api="unknown",
    provider="unknown",
    baseUrl="",
    reasoning=False,
    input=[],
    cost={"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0},
    contextWindow=0,
    maxTokens=0,
)


class _PendingMessageQueue:
    def __init__(self, mode: QueueMode) -> None:
        self._messages: list[AgentMessage] = []
        self.mode: QueueMode = mode

    def enqueue(self, message: AgentMessage) -> None:
        self._messages.append(message)

    def has_items(self) -> bool:
        return len(self._messages) > 0

    def drain(self) -> list[AgentMessage]:
        if self.mode == "all":
            drained = list(self._messages)
            self._messages = []
            return drained
        first = self._messages[0] if self._messages else None
        if first is None:
            return []
        self._messages = self._messages[1:]
        return [first]

    def clear(self) -> None:
        self._messages = []


class _AgentMutableState:
    def __init__(
        self,
        initial_state: dict[str, Any] | None = None,
    ) -> None:
        self._tools: list[AgentTool] = []
        self._messages: list[AgentMessage] = []
        if initial_state is not None:
            self._tools = list(initial_state.get("tools", []))
            self._messages = list(initial_state.get("messages", []))
        self.systemPrompt: str = (
            (initial_state or {}).get("systemPrompt", "") or ""
        )
        self.model: Model = (
            (initial_state or {}).get("model") or DEFAULT_MODEL
        )
        self.thinkingLevel: ThinkingLevel = (
            (initial_state or {}).get("thinkingLevel") or "off"
        )
        self.isStreaming: bool = False
        self.streamingMessage: AgentMessage | None = None
        self.pendingToolCalls: set[str] = set()
        self.errorMessage: str | None = None

    def _get_tools(self) -> list[AgentTool]:
        return self._tools

    def _set_tools(self, tools: list[AgentTool]) -> None:
        self._tools = list(tools)

    def _get_messages(self) -> list[AgentMessage]:
        return self._messages

    def _set_messages(self, messages: list[AgentMessage]) -> None:
        self._messages = list(messages)


class Agent:
    def __init__(self, options: dict[str, Any] | None = None) -> None:
        options = options or {}
        self._state = _AgentMutableState(options.get("initialState"))
        self.convertToLlm: Callable[..., Any] = (
            options.get("convertToLlm") or _default_convert_to_llm
        )
        self.transformContext: Callable[..., Any] | None = options.get(
            "transformContext"
        )
        self.runtime: AgentCoreStreamRuntimeDeps | None = options.get("runtime")
        self.streamFn = resolve_agent_core_stream_fn(
            options.get("runtime"), options.get("streamFn")
        )
        self.getApiKey: Callable[..., Any] | None = options.get("getApiKey")
        self.onPayload: Any = options.get("onPayload")
        self.onResponse: Any = options.get("onResponse")
        self.beforeToolCall: Callable[..., Any] | None = options.get(
            "beforeToolCall"
        )
        self.resolveDeferredTool: Callable[..., Any] | None = options.get(
            "resolveDeferredTool"
        )
        self.afterToolCall: Callable[..., Any] | None = options.get(
            "afterToolCall"
        )
        self.prepareNextTurn: Callable[..., Any] | None = options.get(
            "prepareNextTurn"
        )
        self._steering_queue = _PendingMessageQueue(
            options.get("steeringMode") or "one-at-a-time"
        )
        self._follow_up_queue = _PendingMessageQueue(
            options.get("followUpMode") or "one-at-a-time"
        )
        self.sessionId: str | None = options.get("sessionId")
        self.thinkingBudgets: Any = options.get("thinkingBudgets")
        self.transport: str = options.get("transport") or "auto"
        self.maxRetryDelayMs: int | None = options.get("maxRetryDelayMs")
        self.toolExecution: str = options.get("toolExecution") or "parallel"
        self._active_run: dict[str, Any] | None = None
        self._listeners: set[Callable[..., Any]] = set()

    @property
    def state(self) -> AgentState:
        return self._state

    def subscribe(self, listener: Callable[..., Any]) -> Callable[[], None]:
        self._listeners.add(listener)

        def _unsub() -> None:
            self._listeners.discard(listener)

        return _unsub

    @property
    def steeringMode(self) -> QueueMode:
        return self._steering_queue.mode

    @steeringMode.setter
    def steeringMode(self, mode: QueueMode) -> None:
        self._steering_queue.mode = mode

    @property
    def followUpMode(self) -> QueueMode:
        return self._follow_up_queue.mode

    @followUpMode.setter
    def followUpMode(self, mode: QueueMode) -> None:
        self._follow_up_queue.mode = mode

    def steer(self, message: AgentMessage) -> None:
        self._steering_queue.enqueue(message)

    def followUp(self, message: AgentMessage) -> None:
        self._follow_up_queue.enqueue(message)

    def clearSteeringQueue(self) -> None:
        self._steering_queue.clear()

    def clearFollowUpQueue(self) -> None:
        self._follow_up_queue.clear()

    def clearAllQueues(self) -> None:
        self.clearSteeringQueue()
        self.clearFollowUpQueue()

    def hasQueuedMessages(self) -> bool:
        return self._steering_queue.has_items() or self._follow_up_queue.has_items()

    @property
    def signal(self) -> Any | None:
        if self._active_run is None:
            return None
        return self._active_run.get("abortController")

    def abort(self) -> None:
        if self._active_run is not None:
            controller = self._active_run.get("abortController")
            if controller is not None:
                controller.abort()

    async def waitForIdle(self) -> None:
        if self._active_run is None:
            return
        await self._active_run["promise"]

    def reset(self) -> None:
        self._state._messages = []
        self._state.isStreaming = False
        self._state.streamingMessage = None
        self._state.pendingToolCalls = set()
        self._state.errorMessage = None
        self.clearFollowUpQueue()
        self.clearSteeringQueue()

    async def prompt(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> None:
        if self._active_run is not None:
            raise Exception(
                "Agent is already processing a prompt. Use steer() or followUp() to queue messages, or wait for completion."
            )
        messages = self._normalize_prompt_input(input, images)
        await self._run_prompt_messages(messages)

    async def continue_(self) -> None:
        if self._active_run is not None:
            raise Exception("Agent is already processing. Wait for completion before continuing.")
        messages = self._state._messages
        if not messages:
            raise Exception("No messages to continue from")
        last = messages[-1]
        if getattr(last, "role", None) == "assistant":
            queued_steering = self._steering_queue.drain()
            if queued_steering:
                await self._run_prompt_messages(
                    queued_steering, {"skipInitialSteeringPoll": True}
                )
                return
            queued_followups = self._follow_up_queue.drain()
            if queued_followups:
                await self._run_prompt_messages(queued_followups)
                return
            raise Exception("Cannot continue from message role: assistant")
        await self._run_continuation()

    def _normalize_prompt_input(
        self,
        input: str | AgentMessage | list[AgentMessage],
        images: list[ImageContent] | None = None,
    ) -> list[AgentMessage]:
        if isinstance(input, list):
            return input
        if not isinstance(input, str):
            return [input]
        content: list[Any] = [TextContent(text=input)]
        if images:
            content.extend(images)
        return [{"role": "user", "content": content, "timestamp": int(time.time() * 1000)}]

    async def _run_prompt_messages(
        self,
        messages: list[AgentMessage],
        options: dict[str, Any] | None = None,
    ) -> None:
        options = options or {}

        async def _exec(abort_controller: Any) -> None:
            await run_agent_loop(
                messages,
                self._create_context_snapshot(),
                self._create_loop_config(options),
                lambda event: self._process_events(event),
                abort_controller.signal,
                self.streamFn,
            )

        await self._run_with_lifecycle(_exec)

    async def _run_continuation(self) -> None:
        async def _exec(abort_controller: Any) -> None:
            await run_agent_loop_continue(
                self._create_context_snapshot(),
                self._create_loop_config(),
                lambda event: self._process_events(event),
                abort_controller.signal,
                self.streamFn,
            )

        await self._run_with_lifecycle(_exec)

    def _create_context_snapshot(self) -> AgentContext:
        return AgentContext(
            systemPrompt=self._state.systemPrompt,
            messages=list(self._state._messages),
            tools=list(self._state._tools),
        )

    def _create_loop_config(
        self,
        options: dict[str, Any] | None = None,
    ) -> AgentLoopConfig:
        options = options or {}
        skip_initial = options.get("skipInitialSteeringPoll", False)

        async def _steering():
            nonlocal skip_initial
            if skip_initial:
                skip_initial = False
                return []
            return self._steering_queue.drain()

        async def _followup():
            return self._follow_up_queue.drain()

        async def _prepare_next_turn(signal: Any | None = None) -> Any:
            if self.prepareNextTurn is None:
                return None
            result = self.prepareNextTurn(signal)
            if hasattr(result, "__await__"):
                result = await result
            return result

        return AgentLoopConfig(
            model=self._state.model,
            thinkingLevel=self._state.thinkingLevel,
            reasoning=resolve_agent_reasoning_option(
                self._state.model, self._state.thinkingLevel
            ),
            sessionId=self.sessionId,
            onPayload=self.onPayload,
            onResponse=self.onResponse,
            transport=self.transport,
            thinkingBudgets=self.thinkingBudgets,
            maxRetryDelayMs=self.maxRetryDelayMs,
            toolExecution=self.toolExecution,
            beforeToolCall=self.beforeToolCall,
            resolveDeferredTool=self.resolveDeferredTool,
            afterToolCall=self.afterToolCall,
            prepareNextTurn=_prepare_next_turn if self.prepareNextTurn is not None else None,
            convertToLlm=self.convertToLlm,
            transformContext=self.transformContext,
            getApiKey=self.getApiKey,
            getSteeringMessages=_steering,
            getFollowUpMessages=_followup,
        )

    async def _run_with_lifecycle(
        self,
        executor: Callable[[Any], Any],
    ) -> None:
        if self._active_run is not None:
            raise Exception("Agent is already processing.")

        loop = asyncio.get_event_loop()
        abort_controller = _AbortController()
        resolve_future: asyncio.Future = loop.create_future()

        async def _resolve() -> None:
            resolve_future.set_result(None)

        self._active_run = {
            "promise": resolve_future,
            "resolve": _resolve,
            "abortController": abort_controller,
        }
        self._state.isStreaming = True
        self._state.streamingMessage = None
        self._state.errorMessage = None

        try:
            await executor(abort_controller)
        except Exception as error:
            await self._handle_run_failure(error, abort_controller.aborted)
        finally:
            self._finish_run()

    async def _handle_run_failure(self, error: Any, aborted: bool) -> None:
        failure_message = {
            "role": "assistant",
            "content": [{"type": "text", "text": ""}],
            "api": self._state.model.api,
            "provider": self._state.model.provider,
            "model": self._state.model.id,
            "usage": EMPTY_USAGE,
            "stopReason": "aborted" if aborted else "error",
            "errorMessage": str(error),
            "timestamp": int(time.time() * 1000),
        }
        await self._process_events({"type": "message_start", "message": failure_message})
        await self._process_events({"type": "message_end", "message": failure_message})
        await self._process_events({"type": "turn_end", "message": failure_message, "toolResults": []})
        await self._process_events({"type": "agent_end", "messages": [failure_message]})

    def _finish_run(self) -> None:
        self._state.isStreaming = False
        self._state.streamingMessage = None
        self._state.pendingToolCalls = set()
        if self._active_run is not None:
            resolve_fn = self._active_run.get("resolve")
            if resolve_fn is not None:
                try:
                    resolve_fn()
                except Exception:
                    pass
        self._active_run = None

    async def _process_events(self, event: AgentEvent) -> None:
        etype = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
        if etype in ("agent_start", "turn_start", "tool_execution_update"):
            pass
        elif etype == "message_start":
            self._state.streamingMessage = event.get("message") if isinstance(event, dict) else getattr(event, "message")
        elif etype == "message_update":
            self._state.streamingMessage = event.get("message") if isinstance(event, dict) else getattr(event, "message")
        elif etype == "message_end":
            self._state.streamingMessage = None
            msg = event.get("message") if isinstance(event, dict) else getattr(event, "message")
            self._state._messages.append(msg)
        elif etype == "tool_execution_start":
            pending = set(self._state.pendingToolCalls)
            pending.add(event.get("toolCallId"))
            self._state.pendingToolCalls = pending
        elif etype == "tool_execution_end":
            pending = set(self._state.pendingToolCalls)
            pending.discard(event.get("toolCallId"))
            self._state.pendingToolCalls = pending
        elif etype == "turn_end":
            msg = event.get("message") if isinstance(event, dict) else getattr(event, "message")
            if isinstance(msg, dict) and msg.get("role") == "assistant" and msg.get("errorMessage"):
                self._state.errorMessage = msg.get("errorMessage")
        elif etype == "agent_end":
            self._state.streamingMessage = None

        signal = self.signal
        if signal is None:
            raise Exception("Agent listener invoked outside active run")
        for listener in list(self._listeners):
            result = listener(event, signal)
            if hasattr(result, "__await__"):
                await result


class _AbortController:
    def __init__(self) -> None:
        self.aborted: bool = False
        self.signal = self
        self.reason: Any = None

    def abort(self, reason: Any = None) -> None:
        self.aborted = True
        self.reason = reason

    def add_event_listener(self, _type: str, callback: Callable[[Any], Any]) -> None:
        pass
