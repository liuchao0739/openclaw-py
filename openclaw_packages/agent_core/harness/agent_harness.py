from __future__ import annotations

import time
from typing import Any, Callable

from openclaw.llm.core import (
    AssistantMessage,
    ImageContent,
    Model,
)

from ..agent_loop import run_agent_loop
from ..agent_types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    QueueMode,
    ThinkingLevel,
)
from ..reasoning import resolve_agent_reasoning_option
from ..runtime_deps import (
    AgentCoreRuntimeDeps,
    resolve_agent_core_stream_fn,
)
from .compaction.branch_summarization import (
    collect_entries_for_branch_summary,
    generate_branch_summary,
)
from .compaction.compaction import (
    DEFAULT_COMPACTION_SETTINGS,
    compact,
    prepare_compaction,
)
from .harness_types import (
    AbortResult,
    AgentHarnessError,
    AgentHarnessEvent,
    AgentHarnessOwnEvent,
    AgentHarnessPhase,
    AgentHarnessResources,
    AgentHarnessStreamOptions,
    AgentHarnessStreamOptionsPatch,
    BranchSummaryError,
    CompactionError,
    ExecutionEnv,
    NavigateTreeResult,
    SessionError,
    to_error,
)
from .session.session import Session
from .messages import convert_to_llm
from .prompt_template_arguments import format_prompt_template_invocation
from .skills import format_skill_invocation


def _create_user_message(text: str, images: list[ImageContent] | None = None) -> dict[str, Any]:
    content: list[dict[str, Any]] = [{"type": "text", "text": text}]
    if images:
        for img in images:
            content.append(img)
    return {
        "role": "user",
        "content": content,
        "timestamp": int(time.time() * 1000),
    }


def _create_failure_message(model: Model, error: Any, aborted: bool) -> AssistantMessage:
    return AssistantMessage(
        role="assistant",
        content=[{"type": "text", "text": ""}],
        api=model.api,
        provider=model.provider,
        model=model.id,
        stop_reason="aborted" if aborted else "error",
        error_message=str(error) if error is not None else None,
        timestamp=int(time.time() * 1000),
        usage={
            "input": 0,
            "output": 0,
            "cache_read": 0,
            "cache_write": 0,
            "total_tokens": 0,
            "cost": {"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
        },
    )


def _clone_stream_options(
    stream_options: AgentHarnessStreamOptions | None,
) -> AgentHarnessStreamOptions:
    if stream_options is None:
        return AgentHarnessStreamOptions()
    return AgentHarnessStreamOptions(
        transport=stream_options.transport,
        timeoutMs=stream_options.timeoutMs,
        maxRetries=stream_options.maxRetries,
        maxRetryDelayMs=stream_options.maxRetryDelayMs,
        headers=dict(stream_options.headers) if stream_options.headers else None,
        metadata=dict(stream_options.metadata) if stream_options.metadata else None,
        cacheRetention=stream_options.cacheRetention,
    )


def _merge_headers(
    *headers: dict[str, str] | None,
) -> dict[str, str] | None:
    merged: dict[str, str] = {}
    has_headers = False
    for entry in headers:
        if entry is None:
            continue
        for k, v in entry.items():
            merged[k] = v
        has_headers = True
    return merged if has_headers else None


def _apply_stream_options_patch(
    base: AgentHarnessStreamOptions,
    patch: AgentHarnessStreamOptionsPatch | None,
) -> AgentHarnessStreamOptions:
    result = _clone_stream_options(base)
    if patch is None:
        return result

    if patch.transport is not None and hasattr(patch, "transport"):
        result.transport = patch.transport
    if patch.timeoutMs is not None and hasattr(patch, "timeoutMs"):
        result.timeoutMs = patch.timeoutMs
    if patch.maxRetries is not None and hasattr(patch, "maxRetries"):
        result.maxRetries = patch.maxRetries
    if patch.maxRetryDelayMs is not None and hasattr(patch, "maxRetryDelayMs"):
        result.maxRetryDelayMs = patch.maxRetryDelayMs
    if patch.cacheRetention is not None and hasattr(patch, "cacheRetention"):
        result.cacheRetention = patch.cacheRetention

    if patch.headers is not None and hasattr(patch, "headers"):
        if patch.headers is None:
            result.headers = None
        else:
            headers = dict(result.headers) if result.headers else {}
            for key, value in patch.headers.items():
                if value is None:
                    headers.pop(key, None)
                else:
                    headers[key] = value
            result.headers = headers if len(headers) > 0 else None

    if patch.metadata is not None and hasattr(patch, "metadata"):
        if patch.metadata is None:
            result.metadata = None
        else:
            metadata = dict(result.metadata) if result.metadata else {}
            for key, value in patch.metadata.items():
                if value is None:
                    metadata.pop(key, None)
                else:
                    metadata[key] = value
            result.metadata = metadata if len(metadata) > 0 else None

    return result


SUBSCRIBER_EVENT_TYPE = "*"

AgentHarnessHandler = Callable[[Any, Any | None], Any]


def _normalize_harness_error(
    error: Any,
    fallback_code: str,
) -> AgentHarnessError:
    if isinstance(error, AgentHarnessError):
        return error
    cause = to_error(error)
    if isinstance(cause, SessionError):
        return AgentHarnessError("session", cause.message, cause)
    if isinstance(cause, CompactionError):
        return AgentHarnessError("compaction", cause.message, cause)
    if isinstance(cause, BranchSummaryError):
        return AgentHarnessError("branch_summary", cause.message, cause)
    return AgentHarnessError(fallback_code, cause.message, cause)


def _normalize_hook_error(error: Any) -> AgentHarnessError:
    return _normalize_harness_error(error, "hook")


class CoreAgentHarness:
    def __init__(self, options: dict[str, Any]) -> None:
        self.env: ExecutionEnv = options["env"]
        self._session: Session = options["session"]
        self._resources: AgentHarnessResources = options.get("resources") or AgentHarnessResources()
        self._phase: AgentHarnessPhase = "idle"
        self._run_abort_controller: Any | None = None
        self._run_deferred: dict[str, Any] | None = None
        self._pending_session_writes: list[dict[str, Any]] = []
        self._model: Model = options["model"]
        self._thinking_level: ThinkingLevel = options.get("thinkingLevel") or "off"
        self._system_prompt: Any = options["systemPrompt"]
        self._stream_options: AgentHarnessStreamOptions = _clone_stream_options(
            options.get("streamOptions")
        )
        self._get_api_key_and_headers: Any = options.get("getApiKeyAndHeaders")
        self._runtime: AgentCoreRuntimeDeps | None = options.get("runtime")
        self._tools: dict[str, AgentTool] = {}
        for tool in options.get("tools", []) or []:
            self._tools[tool.name] = tool
        self._active_tool_names: list[str] = options.get("activeToolNames") or [
            t.name for t in options.get("tools", []) or []
        ]
        self._steer_queue: list[AgentMessage] = []
        self._steering_queue_mode: QueueMode = options.get("steeringMode") or "one-at-a-time"
        self._follow_up_queue: list[AgentMessage] = []
        self._follow_up_queue_mode: QueueMode = options.get("followUpMode") or "one-at-a-time"
        self._next_turn_queue: list[AgentMessage] = []
        self._handlers: dict[str, set[AgentHarnessHandler]] = {}

    def _get_handlers(self, type: str) -> set[AgentHarnessHandler] | None:
        return self._handlers.get(type)

    async def _emit_own(
        self,
        event: AgentHarnessOwnEvent,
        signal: Any | None = None,
    ) -> None:
        for listener in self._get_handlers(SUBSCRIBER_EVENT_TYPE) or set():
            try:
                result = listener(event, signal)
                if hasattr(result, "__await__"):
                    await result
            except Exception as error:
                raise _normalize_hook_error(error)

    async def _emit_any(
        self,
        event: AgentHarnessEvent,
        signal: Any | None = None,
    ) -> None:
        for listener in self._get_handlers(SUBSCRIBER_EVENT_TYPE) or set():
            try:
                result = listener(event, signal)
                if hasattr(result, "__await__"):
                    await result
            except Exception as error:
                raise _normalize_hook_error(error)

    async def _emit_hook(self, event: Any) -> Any:
        event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
        handlers = self._get_handlers(event_type)
        if not handlers or len(handlers) == 0:
            return None
        last_result: Any = None
        for handler in handlers:
            try:
                result = handler(event)
                if hasattr(result, "__await__"):
                    result = await result
                if result is not None:
                    last_result = result
            except Exception as error:
                raise _normalize_hook_error(error)
        return last_result

    async def _emit_before_provider_request(
        self,
        model: Model,
        session_id: str,
        stream_options: AgentHarnessStreamOptions,
    ) -> AgentHarnessStreamOptions:
        handlers = self._get_handlers("before_provider_request")
        current = _clone_stream_options(stream_options)
        if not handlers or len(handlers) == 0:
            return current
        for handler in handlers:
            try:
                result = handler({
                    "type": "before_provider_request",
                    "model": model,
                    "sessionId": session_id,
                    "streamOptions": _clone_stream_options(current),
                })
                if hasattr(result, "__await__"):
                    result = await result
                if result and result.get("streamOptions"):
                    current = _apply_stream_options_patch(current, result["streamOptions"])
            except Exception as error:
                raise _normalize_hook_error(error)
        return current

    async def _emit_before_provider_payload(
        self,
        model: Model,
        payload: Any,
    ) -> Any:
        handlers = self._get_handlers("before_provider_payload")
        current = payload
        if not handlers or len(handlers) == 0:
            return current
        for handler in handlers:
            try:
                result = handler({
                    "type": "before_provider_payload",
                    "model": model,
                    "payload": current,
                })
                if hasattr(result, "__await__"):
                    result = await result
                if result is not None:
                    current = result.get("payload", current)
            except Exception as error:
                raise _normalize_hook_error(error)
        return current

    async def _emit_queue_update(self) -> None:
        await self._emit_own({
            "type": "queue_update",
            "steer": list(self._steer_queue),
            "followUp": list(self._follow_up_queue),
            "nextTurn": list(self._next_turn_queue),
        })

    def _start_run_deferred(self) -> None:
        deferred: dict[str, Any] = {}

        async def _resolve():
            pass

        deferred["future"] = _resolve()
        self._run_deferred = deferred

    async def _create_turn_state(self) -> dict[str, Any]:
        context = await self._session.build_context()
        resources = self._get_resources()
        session_metadata = await self._session.get_metadata()
        tools = list(self._tools.values())
        active_tools = [
            self._tools[name]
            for name in self._active_tool_names
            if name in self._tools
        ]
        system_prompt = "You are a helpful assistant."
        if isinstance(self._system_prompt, str):
            system_prompt = self._system_prompt
        elif self._system_prompt:
            result = self._system_prompt({
                "env": self.env,
                "session": self._session,
                "model": self._model,
                "thinkingLevel": self._thinking_level,
                "activeTools": active_tools,
                "resources": resources,
            })
            if hasattr(result, "__await__"):
                result = await result
            system_prompt = result
        return {
            "messages": context.messages,
            "resources": resources,
            "streamOptions": _clone_stream_options(self._stream_options),
            "sessionId": session_metadata.id,
            "systemPrompt": system_prompt,
            "model": self._model,
            "thinkingLevel": self._thinking_level,
            "tools": tools,
            "activeTools": active_tools,
        }

    def _create_context(
        self,
        turn_state: dict[str, Any],
        system_prompt: str | None = None,
    ) -> AgentContext:
        return AgentContext(
            systemPrompt=system_prompt if system_prompt is not None else turn_state["systemPrompt"],
            messages=list(turn_state["messages"]),
            tools=list(turn_state["activeTools"]),
        )

    def _create_stream_fn(
        self,
        get_turn_state: Callable[[], dict[str, Any]],
    ) -> Callable[..., Any]:
        async def _stream_fn(model, context, stream_options):
            turn_state = get_turn_state()
            auth_result = None
            if self._get_api_key_and_headers:
                auth_result = self._get_api_key_and_headers(model)
                if hasattr(auth_result, "__await__"):
                    auth_result = await auth_result
            auth = auth_result or {}
            snapshot_options = AgentHarnessStreamOptions(
                transport=turn_state["streamOptions"].transport,
                timeoutMs=turn_state["streamOptions"].timeoutMs,
                maxRetries=turn_state["streamOptions"].maxRetries,
                maxRetryDelayMs=turn_state["streamOptions"].maxRetryDelayMs,
                headers=_merge_headers(
                    turn_state["streamOptions"].headers,
                    auth.get("headers") if auth else None,
                ),
                metadata=turn_state["streamOptions"].metadata,
                cacheRetention=turn_state["streamOptions"].cacheRetention,
            )
            request_options = await self._emit_before_provider_request(
                model,
                turn_state["sessionId"],
                snapshot_options,
            )
            runtime_stream_fn = resolve_agent_core_stream_fn(self._runtime, None)
            merged_options = dict(stream_options) if isinstance(stream_options, dict) else {}
            merged_options.update({
                "cacheRetention": request_options.cacheRetention,
                "headers": request_options.headers,
                "maxRetries": request_options.maxRetries,
                "maxRetryDelayMs": request_options.maxRetryDelayMs,
                "metadata": request_options.metadata,
                "onPayload": lambda payload: self._emit_before_provider_payload(model, payload),
                "onResponse": lambda response: self._emit_own(
                    {
                        "type": "after_provider_response",
                        "status": response.get("status", 0) if isinstance(response, dict) else getattr(response, "status", 0),
                        "headers": dict(response.get("headers", {})) if isinstance(response, dict) else dict(getattr(response, "headers", {})),
                    },
                    merged_options.get("signal"),
                ),
                "sessionId": turn_state["sessionId"],
                "timeoutMs": request_options.timeoutMs,
                "transport": request_options.transport,
                "apiKey": auth.get("apiKey") if auth else None,
            })
            return runtime_stream_fn(model, context, merged_options)
        return _stream_fn

    async def _drain_queued_messages(
        self,
        queue: list[AgentMessage],
        mode: QueueMode,
    ) -> list[AgentMessage]:
        if mode == "all":
            messages = list(queue)
            queue.clear()
        else:
            messages = [queue.pop(0)] if queue else []
        if len(messages) == 0:
            return messages
        try:
            await self._emit_queue_update()
            return messages
        except Exception as error:
            if mode == "all":
                queue.extend(messages)
            else:
                queue.insert(0, messages[0])
            raise _normalize_hook_error(error)

    def _create_loop_config(
        self,
        get_turn_state: Callable[[], dict[str, Any]],
        set_turn_state: Callable[[dict[str, Any]], None],
    ) -> AgentLoopConfig:
        turn_state = get_turn_state()
        config: AgentLoopConfig = {
            "model": turn_state["model"],
            "thinkingLevel": turn_state["thinkingLevel"],
            "reasoning": resolve_agent_reasoning_option(
                turn_state["model"], turn_state["thinkingLevel"]
            ),
            "convertToLlm": convert_to_llm,
        }

        async def _transform_context(messages, signal):
            result = await self._emit_hook({"type": "context", "messages": list(messages)})
            if result and result.get("messages"):
                return result["messages"]
            return messages

        config["transformContext"] = _transform_context

        async def _before_tool_call(args, signal):
            result = await self._emit_hook({
                "type": "tool_call",
                "toolCallId": args.get("toolCallId", ""),
                "toolName": args.get("toolName", ""),
                "input": args.get("input", {}),
            })
            if result:
                return {"block": result.get("block"), "reason": result.get("reason")}
            return None

        config["beforeToolCall"] = _before_tool_call

        async def _after_tool_call(args, signal):
            result = await self._emit_hook({
                "type": "tool_result",
                "toolCallId": args.get("toolCallId", ""),
                "toolName": args.get("toolName", ""),
                "input": args.get("input", {}),
                "content": args.get("content", []),
                "details": args.get("details"),
                "isError": args.get("isError", False),
            })
            if result:
                return {
                    "content": result.get("content"),
                    "details": result.get("details"),
                    "isError": result.get("isError"),
                    "terminate": result.get("terminate"),
                }
            return None

        config["afterToolCall"] = _after_tool_call

        async def _prepare_next_turn(args):
            await self._flush_pending_session_writes()
            next_turn_state = await self._create_turn_state()
            set_turn_state(next_turn_state)
            return {
                "context": self._create_context(next_turn_state),
                "model": next_turn_state["model"],
                "thinkingLevel": next_turn_state["thinkingLevel"],
            }

        config["prepareNextTurn"] = _prepare_next_turn

        async def _get_steering_messages():
            return await self._drain_queued_messages(self._steer_queue, self._steering_queue_mode)

        config["getSteeringMessages"] = _get_steering_messages

        async def _get_follow_up_messages():
            return await self._drain_queued_messages(self._follow_up_queue, self._follow_up_queue_mode)

        config["getFollowUpMessages"] = _get_follow_up_messages

        return config

    def _validate_tool_names(
        self,
        tool_names: list[str],
        tools: dict[str, AgentTool] | None = None,
    ) -> None:
        if tools is None:
            tools = self._tools
        missing = [name for name in tool_names if name not in tools]
        if len(missing) > 0:
            raise AgentHarnessError("invalid_argument", f"Unknown tool(s): {', '.join(missing)}")

    async def _flush_pending_session_writes(self) -> None:
        while len(self._pending_session_writes) > 0:
            write = self._pending_session_writes[0]
            write_type = write.get("type", "")
            if write_type == "message":
                await self._session.append_message(write["message"])
            elif write_type == "model_change":
                await self._session.append_model_change(write["provider"], write["modelId"])
            elif write_type == "thinking_level_change":
                await self._session.append_thinking_level_change(write["thinkingLevel"])
            elif write_type == "custom":
                await self._session.append_custom_entry(write["customType"], write.get("data"))
            elif write_type == "custom_message":
                await self._session.append_custom_message_entry(
                    write["customType"],
                    write["content"],
                    write.get("display", False),
                    write.get("details"),
                )
            elif write_type == "label":
                await self._session.append_label(write["targetId"], write.get("label"))
            elif write_type == "session_info":
                await self._session.append_session_name(write.get("name", ""))
            elif write_type == "leaf":
                await self._session.get_storage().setLeafId(write["targetId"])
            self._pending_session_writes.pop(0)

    async def _handle_agent_event(
        self,
        event: AgentEvent,
        signal: Any | None = None,
    ) -> None:
        event_type = event.get("type") if isinstance(event, dict) else getattr(event, "type", None)
        if event_type == "message_end":
            await self._session.append_message(event["message"] if isinstance(event, dict) else event.message)
            await self._emit_any(event, signal)
            return
        if event_type == "turn_end":
            event_error = None
            try:
                await self._emit_any(event, signal)
            except Exception as error:
                event_error = error
            had_pending_mutations = len(self._pending_session_writes) > 0
            await self._flush_pending_session_writes()
            if event_error:
                raise _to_error_object(event_error, "Non-Error thrown")
            await self._emit_own({"type": "save_point", "hadPendingMutations": had_pending_mutations})
            return
        if event_type == "agent_end":
            await self._flush_pending_session_writes()
            self._phase = "idle"
            await self._emit_any(event, signal)
            await self._emit_own(
                {"type": "settled", "nextTurnCount": len(self._next_turn_queue)},
                signal,
            )
            return
        await self._emit_any(event, signal)

    async def _emit_run_failure(
        self,
        model: Model,
        error: Any,
        aborted: bool,
        signal: Any,
    ) -> list[AgentMessage]:
        failure_message = _create_failure_message(model, error, aborted)
        await self._handle_agent_event({"type": "message_start", "message": failure_message}, signal)
        await self._handle_agent_event({"type": "message_end", "message": failure_message}, signal)
        await self._handle_agent_event(
            {"type": "turn_end", "message": failure_message, "toolResults": []},
            signal,
        )
        await self._handle_agent_event(
            {"type": "agent_end", "messages": [failure_message]},
            signal,
        )
        return [failure_message]

    async def _execute_turn(
        self,
        turn_state: dict[str, Any],
        text: str,
        options: dict[str, Any] | None = None,
    ) -> AssistantMessage:
        active_turn_state = [turn_state]
        messages: list[AgentMessage] = [_create_user_message(text, options.get("images") if options else None)]
        if len(self._next_turn_queue) > 0:
            queued_messages = list(self._next_turn_queue)
            self._next_turn_queue.clear()
            try:
                await self._emit_queue_update()
            except Exception as error:
                for msg in reversed(queued_messages):
                    self._next_turn_queue.insert(0, msg)
                raise _normalize_hook_error(error)
            messages = queued_messages + [messages[0]]

        before_result = await self._emit_hook({
            "type": "before_agent_start",
            "prompt": text,
            "images": options.get("images") if options else None,
            "systemPrompt": turn_state["systemPrompt"],
            "resources": turn_state["resources"],
        })
        if before_result and before_result.get("messages"):
            messages = messages + before_result["messages"]

        abort_controller = _create_abort_controller()
        get_turn_state = lambda: active_turn_state[0]
        set_turn_state = lambda next_state: active_turn_state.__setitem__(0, next_state)
        self._run_abort_controller = abort_controller

        async def _run():
            try:
                return await run_agent_loop(
                    messages,
                    self._create_context(
                        active_turn_state[0],
                        before_result.get("systemPrompt") if before_result else None,
                    ),
                    self._create_loop_config(get_turn_state, set_turn_state),
                    lambda event: self._handle_agent_event(event, abort_controller.signal),
                    abort_controller.signal,
                    self._create_stream_fn(get_turn_state),
                )
            except Exception as error:
                try:
                    return await self._emit_run_failure(
                        active_turn_state[0]["model"],
                        error,
                        abort_controller.signal.aborted if hasattr(abort_controller.signal, "aborted") else False,
                        abort_controller.signal,
                    )
                except Exception as failure_error:
                    cause = Exception(f"Agent run failed and failure reporting failed: {error}")
                    raise AgentHarnessError("unknown", str(cause), cause)

        try:
            new_messages = await _run()
            for i in range(len(new_messages) - 1, -1, -1):
                message = new_messages[i]
                role = message.get("role") if isinstance(message, dict) else getattr(message, "role", None)
                if role == "assistant":
                    return message
            raise AgentHarnessError(
                "invalid_state",
                "AgentHarness prompt completed without an assistant message",
            )
        finally:
            try:
                await self._flush_pending_session_writes()
            finally:
                self._run_abort_controller = None

    async def prompt(
        self,
        text: str,
        options: dict[str, Any] | None = None,
    ) -> AssistantMessage:
        if self._phase != "idle":
            raise AgentHarnessError("busy", "AgentHarness is busy")
        self._phase = "turn"
        try:
            turn_state = await self._create_turn_state()
            return await self._execute_turn(turn_state, text, options)
        except Exception as error:
            self._phase = "idle"
            raise _normalize_harness_error(error, "unknown")
        finally:
            self._phase = "idle"

    async def skill(
        self,
        name: str,
        additional_instructions: str | None = None,
    ) -> AssistantMessage:
        if self._phase != "idle":
            raise AgentHarnessError("busy", "AgentHarness is busy")
        self._phase = "turn"
        try:
            turn_state = await self._create_turn_state()
            skill = next(
                (c for c in (turn_state["resources"].get("skills") or []) if c.name == name),
                None,
            )
            if skill is None:
                raise AgentHarnessError("invalid_argument", f"Unknown skill: {name}")
            return await self._execute_turn(
                turn_state,
                format_skill_invocation(skill, additional_instructions),
            )
        except Exception as error:
            self._phase = "idle"
            raise _normalize_harness_error(error, "unknown")
        finally:
            self._phase = "idle"

    async def prompt_from_template(
        self,
        name: str,
        args: list[str] | None = None,
    ) -> AssistantMessage:
        if self._phase != "idle":
            raise AgentHarnessError("busy", "AgentHarness is busy")
        self._phase = "turn"
        try:
            turn_state = await self._create_turn_state()
            templates = turn_state["resources"].get("promptTemplates") or []
            template = next(
                (c for c in templates if c.name == name),
                None,
            )
            if template is None:
                raise AgentHarnessError("invalid_argument", f"Unknown prompt template: {name}")
            return await self._execute_turn(
                turn_state,
                format_prompt_template_invocation(template, args or []),
            )
        except Exception as error:
            self._phase = "idle"
            raise _normalize_harness_error(error, "unknown")
        finally:
            self._phase = "idle"

    async def steer(
        self,
        text: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        if self._phase == "idle":
            raise AgentHarnessError("invalid_state", "Cannot steer while idle")
        self._steer_queue.append(_create_user_message(text, options.get("images") if options else None))
        await self._emit_queue_update()

    async def follow_up(
        self,
        text: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        if self._phase == "idle":
            raise AgentHarnessError("invalid_state", "Cannot follow up while idle")
        self._follow_up_queue.append(_create_user_message(text, options.get("images") if options else None))
        await self._emit_queue_update()

    async def next_turn(
        self,
        text: str,
        options: dict[str, Any] | None = None,
    ) -> None:
        self._next_turn_queue.append(_create_user_message(text, options.get("images") if options else None))
        await self._emit_queue_update()

    async def append_message(self, message: AgentMessage) -> None:
        try:
            if self._phase == "idle":
                await self._session.append_message(message)
            else:
                self._pending_session_writes.append({"type": "message", "message": message})
        except Exception as error:
            raise _normalize_harness_error(error, "session")

    async def compact(
        self,
        custom_instructions: str | None = None,
    ) -> dict[str, Any]:
        if self._phase != "idle":
            raise AgentHarnessError("busy", "compact() requires idle harness")
        self._phase = "compaction"
        try:
            model = self._model
            if model is None:
                raise AgentHarnessError("invalid_state", "No model set for compaction")
            auth = None
            if self._get_api_key_and_headers:
                auth = self._get_api_key_and_headers(model)
                if hasattr(auth, "__await__"):
                    auth = await auth
            if not auth:
                raise AgentHarnessError("auth", "No auth available for compaction")
            branch_entries = await self._session.get_branch()
            preparation_result = prepare_compaction(branch_entries, DEFAULT_COMPACTION_SETTINGS)
            if preparation_result is None:
                raise AgentHarnessError("compaction", "Nothing to compact")

            hook_result = await self._emit_hook({
                "type": "session_before_compact",
                "preparation": preparation_result,
                "branchEntries": branch_entries,
                "customInstructions": custom_instructions,
                "signal": _create_abort_controller().signal,
            })
            if hook_result and hook_result.get("cancel"):
                raise AgentHarnessError("compaction", "Compaction cancelled")

            provided = hook_result.get("compaction") if hook_result else None
            if provided:
                result = provided
            else:
                try:
                    result = await compact(
                        preparation_result,
                        model,
                        auth.get("apiKey"),
                        auth.get("headers"),
                        custom_instructions,
                        _create_abort_controller().signal,
                        self._thinking_level,
                        None,
                        self._runtime,
                    )
                except CompactionError as e:
                    raise AgentHarnessError("compaction", e.message, e)
            entry_id = await self._session.append_compaction(
                result.summary if hasattr(result, "summary") else result.get("summary", ""),
                result.firstKeptEntryId if hasattr(result, "firstKeptEntryId") else result.get("firstKeptEntryId", ""),
                result.tokensBefore if hasattr(result, "tokensBefore") else result.get("tokensBefore", 0),
                result.details if hasattr(result, "details") else result.get("details"),
                provided is not None,
            )
            entry = await self._session.get_entry(entry_id)
            if entry and entry.type == "compaction":
                await self._emit_own({
                    "type": "session_compact",
                    "compactionEntry": entry,
                    "fromHook": provided is not None,
                })
            return {
                "summary": result.summary if hasattr(result, "summary") else result.get("summary", ""),
                "firstKeptEntryId": result.firstKeptEntryId if hasattr(result, "firstKeptEntryId") else result.get("firstKeptEntryId", ""),
                "tokensBefore": result.tokensBefore if hasattr(result, "tokensBefore") else result.get("tokensBefore", 0),
                "details": result.details if hasattr(result, "details") else result.get("details"),
            }
        except Exception as error:
            raise _normalize_harness_error(error, "compaction")
        finally:
            self._phase = "idle"

    async def navigate_tree(
        self,
        target_id: str,
        options: dict[str, Any] | None = None,
    ) -> NavigateTreeResult:
        if self._phase != "idle":
            raise AgentHarnessError("busy", "navigateTree() requires idle harness")
        self._phase = "branch_summary"
        try:
            old_leaf_id = await self._session.get_leaf_id()
            if old_leaf_id == target_id:
                return NavigateTreeResult(cancelled=False)

            target_entry = await self._session.get_entry(target_id)
            if target_entry is None:
                raise AgentHarnessError("invalid_argument", f"Entry {target_id} not found")

            entries_result = await collect_entries_for_branch_summary(
                self._session,
                old_leaf_id,
                target_id,
            )
            entries = entries_result.entries
            common_ancestor_id = entries_result.commonAncestorId

            preparation = {
                "targetId": target_id,
                "oldLeafId": old_leaf_id,
                "commonAncestorId": common_ancestor_id,
                "entriesToSummarize": entries,
                "userWantsSummary": (options or {}).get("summarize", False),
                "customInstructions": (options or {}).get("customInstructions"),
                "replaceInstructions": (options or {}).get("replaceInstructions"),
                "label": (options or {}).get("label"),
            }

            signal = _create_abort_controller()
            hook_result = await self._emit_hook({
                "type": "session_before_tree",
                "preparation": preparation,
                "signal": signal.signal,
            })
            if hook_result and hook_result.get("cancel"):
                return NavigateTreeResult(cancelled=True)

            summary_entry = None
            summary_text = hook_result.get("summary", {}).get("summary") if hook_result else None
            summary_details = hook_result.get("summary", {}).get("details") if hook_result else None

            summarize = (options or {}).get("summarize", False)
            if not summary_text and summarize and len(entries) > 0:
                model = self._model
                if model is None:
                    raise AgentHarnessError("invalid_state", "No model set for branch summary")
                auth = None
                if self._get_api_key_and_headers:
                    auth = self._get_api_key_and_headers(model)
                    if hasattr(auth, "__await__"):
                        auth = await auth
                if not auth:
                    raise AgentHarnessError("auth", "No auth available for branch summary")

                try:
                    branch_summary = await generate_branch_summary(entries, {
                        "model": model,
                        "apiKey": auth.get("apiKey", ""),
                        "headers": auth.get("headers"),
                        "signal": _create_abort_controller().signal,
                        "runtime": self._runtime,
                        "customInstructions": (hook_result or {}).get("customInstructions") or (options or {}).get("customInstructions"),
                        "replaceInstructions": (hook_result or {}).get("replaceInstructions") or (options or {}).get("replaceInstructions"),
                    })
                except BranchSummaryError as e:
                    if e.code == "aborted":
                        return NavigateTreeResult(cancelled=True)
                    raise AgentHarnessError("branch_summary", e.message, e)
                summary_text = branch_summary.summary
                summary_details = {
                    "readFiles": branch_summary.read_files,
                    "modifiedFiles": branch_summary.modified_files,
                }

            editor_text = None
            new_leaf_id: str | None = None
            target_type = target_entry.type if target_entry else None
            if target_type == "message" and target_entry.message.get("role") == "user":
                new_leaf_id = target_entry.parentId
                content = target_entry.message.get("content")
                if isinstance(content, str):
                    editor_text = content
                elif isinstance(content, list):
                    editor_text = "".join(
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
            elif target_type == "custom_message":
                new_leaf_id = target_entry.parentId
                content = target_entry.content
                if isinstance(content, str):
                    editor_text = content
                elif isinstance(content, list):
                    editor_text = "".join(
                        c.get("text", "")
                        for c in content
                        if isinstance(c, dict) and c.get("type") == "text"
                    )
            else:
                new_leaf_id = target_id

            summary_id = await self._session.move_to(
                new_leaf_id,
                {
                    "summary": summary_text,
                    "details": summary_details,
                    "fromHook": hook_result is not None and hook_result.get("summary") is not None,
                } if summary_text else None,
            )
            if summary_id:
                entry = await self._session.get_entry(summary_id)
                if entry and entry.type == "branch_summary":
                    summary_entry = entry

            await self._emit_own({
                "type": "session_tree",
                "newLeafId": await self._session.get_leaf_id(),
                "oldLeafId": old_leaf_id,
                "summaryEntry": summary_entry,
                "fromHook": hook_result is not None and hook_result.get("summary") is not None,
            })
            return NavigateTreeResult(
                cancelled=False,
                editorText=editor_text,
                summaryEntry=summary_entry,
            )
        except Exception as error:
            raise _normalize_harness_error(error, "branch_summary")
        finally:
            self._phase = "idle"

    def get_model(self) -> Model:
        return self._model

    def get_thinking_level(self) -> ThinkingLevel:
        return self._thinking_level

    async def set_model(self, model: Model) -> None:
        try:
            previous_model = self._model
            if self._phase == "idle":
                await self._session.append_model_change(model.provider, model.id)
            else:
                self._pending_session_writes.append({
                    "type": "model_change",
                    "provider": model.provider,
                    "modelId": model.id,
                })
            self._model = model
            await self._emit_own({
                "type": "model_select",
                "model": model,
                "previousModel": previous_model,
                "source": "set",
            })
        except Exception as error:
            raise _normalize_harness_error(error, "session")

    async def set_thinking_level(self, level: ThinkingLevel) -> None:
        try:
            previous_level = self._thinking_level
            if self._phase == "idle":
                await self._session.append_thinking_level_change(level)
            else:
                self._pending_session_writes.append({
                    "type": "thinking_level_change",
                    "thinkingLevel": level,
                })
            self._thinking_level = level
            await self._emit_own({
                "type": "thinking_level_select",
                "level": level,
                "previousLevel": previous_level,
            })
        except Exception as error:
            raise _normalize_harness_error(error, "session")

    async def set_active_tools(self, tool_names: list[str]) -> None:
        try:
            self._validate_tool_names(tool_names)
            self._active_tool_names = list(tool_names)
        except Exception as error:
            raise _normalize_harness_error(error, "invalid_argument")

    def get_steering_mode(self) -> QueueMode:
        return self._steering_queue_mode

    async def set_steering_mode(self, mode: QueueMode) -> None:
        self._steering_queue_mode = mode

    def get_follow_up_mode(self) -> QueueMode:
        return self._follow_up_queue_mode

    async def set_follow_up_mode(self, mode: QueueMode) -> None:
        self._follow_up_queue_mode = mode

    def _get_resources(self) -> AgentHarnessResources:
        return AgentHarnessResources(
            skills=list(self._resources.skills) if self._resources.skills else [],
            promptTemplates=list(self._resources.promptTemplates) if self._resources.promptTemplates else [],
        )

    async def set_resources(
        self,
        resources: AgentHarnessResources,
    ) -> None:
        previous_resources = self._get_resources()
        self._resources = AgentHarnessResources(
            skills=list(resources.skills) if resources.skills else [],
            promptTemplates=list(resources.promptTemplates) if resources.promptTemplates else [],
        )
        await self._emit_own({
            "type": "resources_update",
            "resources": self._get_resources(),
            "previousResources": previous_resources,
        })

    def get_stream_options(self) -> AgentHarnessStreamOptions:
        return _clone_stream_options(self._stream_options)

    async def set_stream_options(
        self,
        stream_options: AgentHarnessStreamOptions,
    ) -> None:
        self._stream_options = _clone_stream_options(stream_options)

    async def set_tools(
        self,
        tools: list[AgentTool],
        active_tool_names: list[str] | None = None,
    ) -> None:
        try:
            next_tools = {tool.name: tool for tool in tools}
            next_active_tool_names = (
                list(active_tool_names) if active_tool_names else list(self._active_tool_names)
            )
            self._validate_tool_names(next_active_tool_names, next_tools)
            self._tools = next_tools
            self._active_tool_names = next_active_tool_names
        except Exception as error:
            raise _normalize_harness_error(error, "invalid_argument")

    async def abort(self) -> AbortResult:
        cleared_steer = list(self._steer_queue)
        cleared_follow_up = list(self._follow_up_queue)
        self._steer_queue = []
        self._follow_up_queue = []
        if self._run_abort_controller:
            self._run_abort_controller.abort()
        errors: list[Exception] = []
        try:
            await self._emit_queue_update()
        except Exception as error:
            errors.append(to_error(error))
        try:
            pass
        except Exception as error:
            errors.append(to_error(error))
        try:
            await self._emit_own({
                "type": "abort",
                "clearedSteer": cleared_steer,
                "clearedFollowUp": cleared_follow_up,
            })
        except Exception as error:
            errors.append(to_error(error))
        if len(errors) > 0:
            cause = errors[0] if len(errors) == 1 else Exception(f"Abort completed with errors: {'; '.join(str(e) for e in errors)}")
            raise _normalize_harness_error(cause, "hook")
        return AbortResult(
            clearedSteer=cleared_steer,
            clearedFollowUp=cleared_follow_up,
        )

    async def wait_for_idle(self) -> None:
        pass

    def subscribe(
        self,
        listener: Callable[[AgentHarnessEvent, Any | None], Any],
    ) -> Callable[[], None]:
        handlers = self._handlers.get(SUBSCRIBER_EVENT_TYPE)
        if handlers is None:
            handlers = set()
            self._handlers[SUBSCRIBER_EVENT_TYPE] = handlers
        handlers.add(listener)

        def _unsubscribe() -> None:
            handlers.discard(listener)

        return _unsubscribe

    def on(
        self,
        type: str,
        handler: Callable[[Any], Any],
    ) -> Callable[[], None]:
        handlers = self._handlers.get(type)
        if handlers is None:
            handlers = set()
            self._handlers[type] = handlers
        handlers.add(handler)

        def _unsubscribe() -> None:
            handlers.discard(handler)

        return _unsubscribe


AgentHarness = CoreAgentHarness


class _AbortSignal:
    def __init__(self) -> None:
        self.aborted = False
        self.reason: Any = None

    def abort(self) -> None:
        self.aborted = True


class _AbortController:
    def __init__(self) -> None:
        self.signal = _AbortSignal()

    def abort(self) -> None:
        self.signal.abort()


def _create_abort_controller() -> _AbortController:
    return _AbortController()


def _to_error_object(value: Any, fallback_message: str) -> Exception:
    if isinstance(value, Exception):
        return value
    if isinstance(value, str):
        return Exception(value)
    error = Exception(fallback_message)
    if isinstance(value, dict):
        for k, v in value.items():
            setattr(error, k, v)
    return error