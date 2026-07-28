from __future__ import annotations

import asyncio
from typing import Any, Callable

from openclaw.llm.core import (
    AssistantMessage,
    Context,
    Model,
    Usage,
)
from openclaw.llm.event_stream import (
    AssistantMessageEvent,
    AssistantMessageEventStream,
    EventStream,
    create_assistant_message_event_stream,
)
from openclaw_packages.llm_core.validation import (
    validate_tool_arguments as _validate_tool_arguments,
)

from .agent_types import (
    AgentContext,
    AgentEvent,
    AgentLoopConfig,
    AgentMessage,
    AgentTool,
    AgentToolCall,
    AgentToolResult,
    BeforeToolCallContext,
)
from .reasoning import resolve_agent_reasoning_option
from .runtime_deps import resolve_agent_core_stream_fn

EMPTY_USAGE = Usage(
    input=0,
    output=0,
    cache_read=0,
    cache_write=0,
    total_tokens=0,
    cost={"input": 0, "output": 0, "cacheRead": 0, "cacheWrite": 0, "total": 0},
)


def _append_text_delta_to_assistant_message(
    message: AssistantMessage,
    content_index: int,
    delta: str,
) -> AssistantMessage:
    content = list(message.content)
    current = content[content_index] if content_index < len(content) else None
    if current is not None and getattr(current, "type", None) == "text":
        from copy import deepcopy

        new_block = deepcopy(current)
        new_block.text = current.text + delta
        content[content_index] = new_block
    else:
        from openclaw.llm.core import TextContent

        content.insert(content_index, TextContent(text=delta))
    message.content = content
    return message


def _resolve_assistant_message_update(
    event: AssistantMessageEvent,
    current_message: AssistantMessage,
) -> AssistantMessage:
    if hasattr(event, "partial") and event.partial is not None:
        return event.partial
    if getattr(event, "type", None) == "text_delta":
        return _append_text_delta_to_assistant_message(
            current_message,
            getattr(event, "contentIndex", 0),
            getattr(event, "delta", ""),
        )
    return current_message


AgentEventSink = Callable[[AgentEvent], Any]


def create_agent_stream() -> EventStream:
    return create_assistant_message_event_stream()


def _create_loop_failure_message(
    config: AgentLoopConfig,
    error: Any,
    aborted: bool,
) -> AssistantMessage:
    model: Model = config.get("model")  # type: ignore[assignment]
    return AssistantMessage(
        role="assistant",
        content=[{"type": "text", "text": ""}],
        api=model.api,
        provider=model.provider,
        model=model.id,
        usage=EMPTY_USAGE,
        stop_reason="aborted" if aborted else "error",
        error_message=str(error) if error is not None else None,
        timestamp=__import__("time").time_ns() // 1_000_000,
    )


async def _push_loop_failure(
    stream: AssistantMessageEventStream,
    config: AgentLoopConfig,
    error: Any,
    aborted: bool,
) -> None:
    failure_message = _create_loop_failure_message(config, error, aborted)
    await stream.push({"type": "message_start", "message": failure_message})
    await stream.push({"type": "message_end", "message": failure_message})
    await stream.push(
        {"type": "turn_end", "message": failure_message, "toolResults": []}
    )
    await stream.push(
        {"type": "agent_end", "messages": [failure_message]}
    )


async def agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any | None = None,
    stream_fn: Callable[..., AssistantMessageEventStream] | None = None,
    runtime: Any | None = None,
) -> AssistantMessageEventStream:
    stream = create_agent_stream()

    async def _run():
        try:
            messages = await run_agent_loop(
                prompts,
                context,
                config,
                lambda event: stream.push(event),
                signal,
                stream_fn,
                runtime,
            )
            await stream.end(messages)
        except Exception as error:
            await _push_loop_failure(stream, config, error, signal.aborted if signal else False)

    asyncio.create_task(_run())
    return stream


async def agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any | None = None,
    stream_fn: Callable[..., AssistantMessageEventStream] | None = None,
    runtime: Any | None = None,
) -> AssistantMessageEventStream:
    if len(context.messages) == 0:
        raise Exception("Cannot continue: no messages in context")

    last = context.messages[-1]
    if getattr(last, "role", None) == "assistant":
        raise Exception("Cannot continue from message role: assistant")

    stream = create_agent_stream()

    async def _run():
        try:
            messages = await run_agent_loop_continue(
                context,
                config,
                lambda event: stream.push(event),
                signal,
                stream_fn,
                runtime,
            )
            await stream.end(messages)
        except Exception as error:
            await _push_loop_failure(stream, config, error, signal.aborted if signal else False)

    asyncio.create_task(_run())
    return stream


async def run_agent_loop(
    prompts: list[AgentMessage],
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Any | None = None,
    stream_fn: Callable[..., AssistantMessageEventStream] | None = None,
    runtime: Any | None = None,
) -> list[AgentMessage]:
    new_messages: list[AgentMessage] = list(prompts)
    current_context: AgentContext = AgentContext(
        systemPrompt=context.systemPrompt,
        messages=list(context.messages) + list(prompts),
        tools=list(context.tools) if context.tools else None,
    )

    await emit({"type": "agent_start"})
    await emit({"type": "turn_start"})
    for prompt in prompts:
        await emit({"type": "message_start", "message": prompt})
        await emit({"type": "message_end", "message": prompt})

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn, runtime)
    return new_messages


async def run_agent_loop_continue(
    context: AgentContext,
    config: AgentLoopConfig,
    emit: AgentEventSink,
    signal: Any | None = None,
    stream_fn: Callable[..., AssistantMessageEventStream] | None = None,
    runtime: Any | None = None,
) -> list[AgentMessage]:
    if len(context.messages) == 0:
        raise Exception("Cannot continue: no messages in context")
    if getattr(context.messages[-1], "role", None) == "assistant":
        raise Exception("Cannot continue from message role: assistant")

    new_messages: list[AgentMessage] = []
    current_context: AgentContext = AgentContext(
        systemPrompt=context.systemPrompt,
        messages=list(context.messages),
        tools=list(context.tools) if context.tools else None,
    )

    await emit({"type": "agent_start"})
    await emit({"type": "turn_start"})

    await _run_loop(current_context, new_messages, config, signal, emit, stream_fn, runtime)
    return new_messages


async def _stop_if_aborted(
    signal: Any | None,
    config: AgentLoopConfig,
    emit: AgentEventSink,
) -> bool:
    if signal is None or not getattr(signal, "aborted", False):
        return False
    reason = getattr(signal, "reason", None)
    aborted_message = _create_loop_failure_message(
        config,
        reason if reason is not None else Exception("Agent run aborted"),
        True,
    )
    new_messages: list[AgentMessage] = [aborted_message]
    await emit({"type": "message_start", "message": aborted_message})
    await emit({"type": "message_end", "message": aborted_message})
    await emit({"type": "turn_end", "message": aborted_message, "toolResults": []})
    await emit({"type": "agent_end", "messages": new_messages})
    return True


async def _run_loop(
    initial_context: AgentContext,
    new_messages: list[AgentMessage],
    initial_config: AgentLoopConfig,
    signal: Any | None,
    emit: AgentEventSink,
    stream_fn: Callable[..., AssistantMessageEventStream] | None,
    runtime: Any | None,
) -> None:
    current_context = initial_context
    config = initial_config
    first_turn = True
    turn_open = True
    pending_messages: list[AgentMessage] = []
    steering_fn = config.get("getSteeringMessages")
    if steering_fn is not None:
        result = steering_fn()
        if hasattr(result, "__await__"):
            result = await result
        pending_messages = list(result) if result else []

    while True:
        has_more_tool_calls = True

        while has_more_tool_calls or len(pending_messages) > 0:
            if await _stop_if_aborted(signal, config, emit):
                return

            if not first_turn:
                await emit({"type": "turn_start"})
                turn_open = True
            else:
                first_turn = False

            if len(pending_messages) > 0:
                for message in pending_messages:
                    await emit({"type": "message_start", "message": message})
                    await emit({"type": "message_end", "message": message})
                    current_context.messages.append(message)
                    new_messages.append(message)

            if await _stop_if_aborted(signal, config, emit):
                return

            message = await _stream_assistant_response(
                current_context, config, signal, emit, stream_fn, runtime
            )
            new_messages.append(message)

            if getattr(message, "stop_reason", None) in ("error", "aborted"):
                await emit(
                    {"type": "turn_end", "message": message, "toolResults": []}
                )
                await emit({"type": "agent_end", "messages": new_messages})
                return

            tool_calls = [
                c for c in message.content if getattr(c, "type", None) == "toolCall"
            ]

            tool_results: list[Any] = []
            has_more_tool_calls = False
            if len(tool_calls) > 0:
                executed = await _execute_tool_calls(
                    current_context, message, config, signal, emit
                )
                tool_results.extend(executed["messages"])
                has_more_tool_calls = not executed["terminate"]

                for result in tool_results:
                    current_context.messages.append(result)
                    new_messages.append(result)

            await emit(
                {"type": "turn_end", "message": message, "toolResults": tool_results}
            )
            turn_open = False
            if await _stop_if_aborted(signal, config, emit):
                return

            next_turn_context = {
                "message": message,
                "toolResults": tool_results,
                "context": current_context,
                "newMessages": new_messages,
            }
            prepare_next = config.get("prepareNextTurn")
            if prepare_next is not None:
                result = prepare_next(next_turn_context)
                if hasattr(result, "__await__"):
                    result = await result
                if result is not None:
                    if result.get("context") is not None:
                        current_context = result["context"]
                    next_model = result.get("model", config.get("model"))
                    next_thinking = result.get("thinkingLevel", config.get("thinkingLevel"))
                    should_resolve = (
                        result.get("thinkingLevel") is not None
                        or (result.get("model") is not None and next_thinking is not None)
                    )
                    if should_resolve and next_thinking is not None:
                        next_reasoning = resolve_agent_reasoning_option(
                            next_model, next_thinking
                        )
                    else:
                        next_reasoning = config.get("reasoning")
                    config = dict(config)  # type: ignore[arg-type]
                    config["model"] = next_model
                    config["thinkingLevel"] = next_thinking
                    config["reasoning"] = next_reasoning

            should_stop = config.get("shouldStopAfterTurn")
            if should_stop is not None:
                stop_context = {
                    "message": message,
                    "toolResults": tool_results,
                    "context": current_context,
                    "newMessages": new_messages,
                }
                result = should_stop(stop_context)
                if hasattr(result, "__await__"):
                    result = await result
                if result:
                    await emit({"type": "agent_end", "messages": new_messages})
                    return

            pending_messages = []
            if steering_fn is not None:
                result = steering_fn()
                if hasattr(result, "__await__"):
                    result = await result
                pending_messages = list(result) if result else []
            if await _stop_if_aborted(signal, config, emit):
                return

        followup_fn = config.get("getFollowUpMessages")
        followup_messages: list[AgentMessage] = []
        if followup_fn is not None:
            result = followup_fn()
            if hasattr(result, "__await__"):
                result = await result
            followup_messages = list(result) if result else []
        if len(followup_messages) > 0:
            pending_messages = followup_messages
            continue

        break

    await emit({"type": "agent_end", "messages": new_messages})


async def _stream_assistant_response(
    context: AgentContext,
    config: AgentLoopConfig,
    signal: Any | None,
    emit: AgentEventSink,
    stream_fn: Callable[..., AssistantMessageEventStream] | None,
    runtime: Any | None,
) -> AssistantMessage:
    messages = context.messages
    transform = config.get("transformContext")
    if transform is not None:
        result = transform(messages, signal)
        if hasattr(result, "__await__"):
            result = await result
        messages = result

    convert_to_llm = config.get("convertToLlm")
    if convert_to_llm is None:
        llm_messages = []
    else:
        llm_messages = convert_to_llm(messages)
        if hasattr(llm_messages, "__await__"):
            llm_messages = await llm_messages

    llm_context = Context(
        system_prompt=context.systemPrompt,
        messages=llm_messages,
        tools=list(context.tools) if context.tools else [],
    )

    resolve_fn = resolve_agent_core_stream_fn(runtime, stream_fn)

    get_api_key_fn = config.get("getApiKey")
    resolved_api_key = config.get("apiKey")
    if get_api_key_fn is not None:
        key_result = get_api_key_fn(config.get("model").provider)  # type: ignore[union-attr]
        if hasattr(key_result, "__await__"):
            key_result = await key_result
        if key_result is not None:
            resolved_api_key = key_result

    stream_options = dict(config)
    stream_options["apiKey"] = resolved_api_key
    stream_options["signal"] = signal

    response = resolve_fn(config.get("model"), llm_context, stream_options)

    partial_message: AssistantMessage | None = None
    added_partial = False

    async for event in response:
        event_type = getattr(event, "type", None)
        if event_type == "start":
            message = getattr(event, "partial", None)
            partial_message = message
            context.messages.append(message)
            added_partial = True
            await emit({"type": "message_start", "message": dict(message)})
        elif event_type in (
            "text_start",
            "text_delta",
            "text_end",
            "thinking_start",
            "thinking_delta",
            "thinking_end",
            "toolcall_start",
            "toolcall_delta",
            "toolcall_end",
        ):
            if partial_message is not None:
                message = _resolve_assistant_message_update(event, partial_message)
                partial_message = message
                context.messages[-1] = message
                await emit(
                    {
                        "type": "message_update",
                        "assistantMessageEvent": event,
                        "message": dict(message),
                    }
                )
        elif event_type in ("done", "error"):
            final = response.result()
            if hasattr(final, "__await__"):
                final = await final
            if added_partial:
                context.messages[-1] = final
            else:
                context.messages.append(final)
                await emit({"type": "message_start", "message": dict(final)})
            await emit({"type": "message_end", "message": final})
            return final

    final = response.result()
    if hasattr(final, "__await__"):
        final = await final
    if added_partial:
        context.messages[-1] = final
    else:
        context.messages.append(final)
        await emit({"type": "message_start", "message": dict(final)})
    await emit({"type": "message_end", "message": final})
    return final


def create_error_tool_result(message: str) -> AgentToolResult:
    from openclaw.llm.core import TextContent

    return AgentToolResult(
        content=[TextContent(text=message)],
        details={},
        progress=None,
        terminate=False,
    )


def _validate_tool_arguments(tool: AgentTool, tool_call: AgentToolCall) -> Any:
    tool_dict = {
        "name": tool.name,
        "description": getattr(tool, "description", ""),
        "parameters": tool.parameters,
    }
    call_dict = {"name": tool_call.name, "arguments": tool_call.arguments}
    return _validate_tool_arguments(tool_dict, call_dict)


async def _resolve_tool_call_tool(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: AgentToolCall,
    config: AgentLoopConfig,
    signal: Any | None,
    resolved_tool_calls: dict[str, Any] | None,
) -> dict[str, Any]:
    if resolved_tool_calls is not None and tool_call.id in resolved_tool_calls:
        return resolved_tool_calls[tool_call.id]
    resolution: dict[str, Any]
    try:
        tool = None
        if current_context.tools is not None:
            tool = next(
                (t for t in current_context.tools if t.name == tool_call.name),
                None,
            )
        if tool is None:
            resolver = config.get("resolveDeferredTool")
            if resolver is not None:
                ctx = {
                    "assistantMessage": assistant_message,
                    "toolCall": tool_call,
                    "context": current_context,
                }
                resolved = resolver(ctx, signal)
                if hasattr(resolved, "__await__"):
                    resolved = await resolved
                if resolved is not None:
                    if resolved.name != tool_call.name:
                        raise Exception(
                            f'Deferred tool resolver returned "{resolved.name}" '
                            f'for requested "{tool_call.name}"'
                        )
                    tool = resolved
                    if current_context.tools is not None:
                        current_context.tools.append(tool)
                    else:
                        current_context.tools = [tool]
        resolution = {"kind": "resolved", "tool": tool}
    except Exception as error:
        resolution = {"kind": "error", "error": error}
    if resolved_tool_calls is not None:
        resolved_tool_calls[tool_call.id] = resolution
    return resolution


async def _prepare_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_call: AgentToolCall,
    config: AgentLoopConfig,
    signal: Any | None,
    resolved_tool_calls: dict[str, Any] | None,
) -> dict[str, Any]:
    resolution = await _resolve_tool_call_tool(
        current_context,
        assistant_message,
        tool_call,
        config,
        signal,
        resolved_tool_calls,
    )
    if resolution["kind"] == "error":
        error = resolution["error"]
        msg = error.message if hasattr(error, "message") else str(error)
        if signal is not None and getattr(signal, "aborted", False):
            msg = "Operation aborted"
        return {
            "kind": "immediate",
            "result": create_error_tool_result(msg),
            "isError": True,
        }

    tool = resolution.get("tool")
    if tool is None:
        return {
            "kind": "immediate",
            "result": create_error_tool_result(f"Tool {tool_call.name} not found"),
            "isError": True,
        }

    try:
        prepared = tool_call
        if tool.prepareArguments is not None:
            new_args = tool.prepareArguments(tool_call.arguments)
            if new_args != tool_call.arguments:
                prepared = AgentToolCall(
                    id=tool_call.id,
                    name=tool_call.name,
                    arguments=new_args,
                )
        validated_args = _validate_tool_arguments(tool, prepared)
        before = config.get("beforeToolCall")
        if before is not None:
            ctx = {
                "assistantMessage": assistant_message,
                "toolCall": prepared,
                "args": validated_args,
                "context": current_context,
            }
            before_result = before(ctx, signal)
            if hasattr(before_result, "__await__"):
                before_result = await before_result
            if signal is not None and getattr(signal, "aborted", False):
                return {
                    "kind": "immediate",
                    "result": create_error_tool_result("Operation aborted"),
                    "isError": True,
                }
            if before_result is not None and before_result.get("block"):
                return {
                    "kind": "immediate",
                    "result": create_error_tool_result(
                        before_result.get("reason") or "Tool execution was blocked"
                    ),
                    "isError": True,
                }
        if signal is not None and getattr(signal, "aborted", False):
            return {
                "kind": "immediate",
                "result": create_error_tool_result("Operation aborted"),
                "isError": True,
            }
        return {
            "kind": "prepared",
            "toolCall": prepared,
            "tool": tool,
            "args": validated_args,
        }
    except Exception as error:
        msg = error.message if hasattr(error, "message") else str(error)
        return {
            "kind": "immediate",
            "result": create_error_tool_result(msg),
            "isError": True,
        }


async def _execute_prepared_tool_call(
    prepared: dict[str, Any],
    signal: Any | None,
    emit: AgentEventSink,
) -> dict[str, Any]:
    update_events: list[Any] = []
    try:
        tool = prepared["tool"]
        tool_call = prepared["toolCall"]
        args = prepared["args"]

        def on_update(partial: AgentToolResult) -> None:
            update_events.append(
                emit(
                    {
                        "type": "tool_execution_update",
                        "toolCallId": tool_call.id,
                        "toolName": tool_call.name,
                        "args": tool_call.arguments,
                        "partialResult": partial,
                    }
                )
            )

        result = tool.execute(tool_call.id, args, signal, on_update)
        if hasattr(result, "__await__"):
            result = await result
        for event in update_events:
            await event
        return {"result": result, "isError": False}
    except Exception as error:
        for event in update_events:
            try:
                await event
            except Exception:
                pass
        msg = error.message if hasattr(error, "message") else str(error)
        return {
            "result": create_error_tool_result(msg),
            "isError": True,
        }


async def _finalize_executed_tool_call(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    prepared: dict[str, Any],
    executed: dict[str, Any],
    config: AgentLoopConfig,
    signal: Any | None,
) -> dict[str, Any]:
    result = executed["result"]
    is_error = executed["isError"]

    after = config.get("afterToolCall")
    if after is not None:
        try:
            ctx = {
                "assistantMessage": assistant_message,
                "toolCall": prepared["toolCall"],
                "args": prepared["args"],
                "result": result,
                "isError": is_error,
                "context": current_context,
            }
            after_result = after(ctx, signal)
            if hasattr(after_result, "__await__"):
                after_result = await after_result
            if after_result is not None:
                content = after_result.get("content")
                if content is not None:
                    result = AgentToolResult(
                        content=content,
                        details=result.details,
                        progress=result.progress,
                        terminate=result.terminate,
                    )
                details = after_result.get("details")
                if details is not None:
                    result = AgentToolResult(
                        content=result.content,
                        details=details,
                        progress=result.progress,
                        terminate=result.terminate,
                    )
                terminate = after_result.get("terminate")
                if terminate is not None:
                    result = AgentToolResult(
                        content=result.content,
                        details=result.details,
                        progress=result.progress,
                        terminate=terminate,
                    )
                new_is_error = after_result.get("isError")
                if new_is_error is not None:
                    is_error = new_is_error
        except Exception as error:
            msg = error.message if hasattr(error, "message") else str(error)
            result = create_error_tool_result(msg)
            is_error = True

    return {
        "toolCall": prepared["toolCall"],
        "result": result,
        "isError": is_error,
        "executionStarted": True,
    }


def _should_terminate_tool_batch(finalized: list[dict[str, Any]]) -> bool:
    return (
        len(finalized) > 0
        and all(f.get("result").terminate is True for f in finalized)
    )


def _create_tool_result_message(finalized: dict[str, Any]) -> dict[str, Any]:
    result = finalized["result"]
    return {
        "role": "toolResult",
        "toolCallId": finalized["toolCall"].id,
        "toolName": finalized["toolCall"].name,
        "content": result.content,
        "details": result.details,
        "isError": finalized["isError"],
        "timestamp": __import__("time").time_ns() // 1_000_000,
    }


async def _emit_tool_execution_end(
    finalized: dict[str, Any],
    emit: AgentEventSink,
) -> None:
    await emit(
        {
            "type": "tool_execution_end",
            "toolCallId": finalized["toolCall"].id,
            "toolName": finalized["toolCall"].name,
            "result": finalized["result"],
            "isError": finalized["isError"],
            "executionStarted": finalized.get("executionStarted", True),
        }
    )


async def _emit_tool_result_message(
    tool_result_message: dict[str, Any],
    emit: AgentEventSink,
) -> None:
    await emit({"type": "message_start", "message": tool_result_message})
    await emit({"type": "message_end", "message": tool_result_message})


async def _execute_tool_calls(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    config: AgentLoopConfig,
    signal: Any | None,
    emit: AgentEventSink,
) -> dict[str, Any]:
    tool_calls: list[AgentToolCall] = [
        c
        for c in assistant_message.content
        if getattr(c, "type", None) == "toolCall"
    ]

    resolved: dict[str, Any] = {}
    has_sequential = False
    if config.get("toolExecution") != "sequential":
        for tool_call in tool_calls:
            resolution = await _resolve_tool_call_tool(
                current_context,
                assistant_message,
                tool_call,
                config,
                signal,
                resolved,
            )
            if (
                resolution["kind"] == "resolved"
                and resolution.get("tool") is not None
                and getattr(resolution["tool"], "executionMode", None) == "sequential"
            ):
                has_sequential = True
                break
            if signal is not None and getattr(signal, "aborted", False):
                break

    if config.get("toolExecution") == "sequential" or has_sequential:
        return await _execute_tool_calls_sequential(
            current_context,
            assistant_message,
            tool_calls,
            resolved,
            config,
            signal,
            emit,
        )
    return await _execute_tool_calls_parallel(
        current_context,
        assistant_message,
        tool_calls,
        resolved,
        config,
        signal,
        emit,
    )


async def _execute_tool_calls_sequential(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[AgentToolCall],
    resolved: dict[str, Any],
    config: AgentLoopConfig,
    signal: Any | None,
    emit: AgentEventSink,
) -> dict[str, Any]:
    finalized: list[dict[str, Any]] = []
    messages: list[Any] = []

    for tool_call in tool_calls:
        await emit(
            {
                "type": "tool_execution_start",
                "toolCallId": tool_call.id,
                "toolName": tool_call.name,
                "args": tool_call.arguments,
            }
        )

        preparation = await _prepare_tool_call(
            current_context,
            assistant_message,
            tool_call,
            config,
            signal,
            resolved,
        )
        if preparation["kind"] == "immediate":
            finalized_entry = {
                "toolCall": tool_call,
                "result": preparation["result"],
                "isError": preparation["isError"],
                "executionStarted": False,
            }
        else:
            executed = await _execute_prepared_tool_call(preparation, signal, emit)
            finalized_entry = await _finalize_executed_tool_call(
                current_context,
                assistant_message,
                preparation,
                executed,
                config,
                signal,
            )

        await _emit_tool_execution_end(finalized_entry, emit)
        tool_result_message = _create_tool_result_message(finalized_entry)
        await _emit_tool_result_message(tool_result_message, emit)
        finalized.append(finalized_entry)
        messages.append(tool_result_message)

        if signal is not None and getattr(signal, "aborted", False):
            break

    return {
        "messages": messages,
        "terminate": _should_terminate_tool_batch(finalized),
    }


async def _execute_tool_calls_parallel(
    current_context: AgentContext,
    assistant_message: AssistantMessage,
    tool_calls: list[AgentToolCall],
    resolved: dict[str, Any],
    config: AgentLoopConfig,
    signal: Any | None,
    emit: AgentEventSink,
) -> dict[str, Any]:
    finalized: list[Any] = []

    for tool_call in tool_calls:
        await emit(
            {
                "type": "tool_execution_start",
                "toolCallId": tool_call.id,
                "toolName": tool_call.name,
                "args": tool_call.arguments,
            }
        )

        preparation = await _prepare_tool_call(
            current_context,
            assistant_message,
            tool_call,
            config,
            signal,
            resolved,
        )
        if preparation["kind"] == "immediate":
            entry = {
                "toolCall": tool_call,
                "result": preparation["result"],
                "isError": preparation["isError"],
                "executionStarted": False,
            }
            await _emit_tool_execution_end(entry, emit)
            finalized.append(entry)
            if signal is not None and getattr(signal, "aborted", False):
                break
            continue

        async def _run(p: dict[str, Any]) -> dict[str, Any]:
            executed = await _execute_prepared_tool_call(p, signal, emit)
            result = await _finalize_executed_tool_call(
                current_context,
                assistant_message,
                p,
                executed,
                config,
                signal,
            )
            await _emit_tool_execution_end(result, emit)
            return result

        finalized.append(_run(preparation))
        if signal is not None and getattr(signal, "aborted", False):
            break

    ordered: list[dict[str, Any]] = []
    for entry in finalized:
        if hasattr(entry, "__await__"):
            result = await entry
            ordered.append(result)
        else:
            ordered.append(entry)

    messages: list[Any] = []
    for fin in ordered:
        tool_result_message = _create_tool_result_message(fin)
        await _emit_tool_result_message(tool_result_message, emit)
        messages.append(tool_result_message)

    return {
        "messages": messages,
        "terminate": _should_terminate_tool_batch(ordered),
    }
