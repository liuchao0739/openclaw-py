"""Minimal agent loop for tool-call rounds."""

from __future__ import annotations

import time
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw.agent_core.messages import AssistantMessage, Message, Tool, ToolResultMessage, UserMessage
from openclaw.llm.core import Model, TextContent, ToolCall
from openclaw.llm.runtime import assistant_text_message


ToolHandler = Callable[[str, dict[str, Any]], Awaitable[str] | str]
StreamFn = Callable[[Model, list[Message], list[Tool] | None], Awaitable[AssistantMessage]]


async def run_agent_loop(
    *,
    model: Model,
    messages: list[Message],
    tools: list[Tool] | None = None,
    tool_handlers: dict[str, ToolHandler] | None = None,
    stream_fn: StreamFn | None = None,
    max_rounds: int = 4,
) -> list[Message]:
    """Run a basic tool-call loop until the model stops or max_rounds is reached."""
    transcript = list(messages)
    handlers = tool_handlers or {}

    async def default_stream_fn(
        active_model: Model,
        active_messages: list[Message],
        active_tools: list[Tool] | None,
    ) -> AssistantMessage:
        last_user = next(
            (m.content for m in reversed(active_messages) if isinstance(m, UserMessage)),
            "",
        )
        text = last_user if isinstance(last_user, str) else "ok"
        if active_tools and "echo" in {tool.name for tool in active_tools}:
            return AssistantMessage(
                api=active_model.api,
                provider=active_model.provider,
                model=active_model.id,
                content=[
                    ToolCall(id="call_1", name="echo", arguments={"text": text}),
                ],
                stopReason="toolUse",
                timestamp=int(time.time() * 1000),
            )
        return assistant_text_message(active_model, f"reply:{text}", timestamp=int(time.time() * 1000))

    llm = stream_fn or default_stream_fn

    for _ in range(max_rounds):
        assistant = await llm(model, transcript, tools)
        transcript.append(assistant)

        tool_calls = [block for block in assistant.content if isinstance(block, ToolCall)]
        if not tool_calls:
            break

        now = int(time.time() * 1000)
        for tool_call in tool_calls:
            handler = handlers.get(tool_call.name)
            if handler is None:
                result_text = f"unknown tool: {tool_call.name}"
                is_error = True
            else:
                maybe = handler(tool_call.name, tool_call.arguments)
                result_text = await maybe if hasattr(maybe, "__await__") else maybe
                is_error = False
            transcript.append(
                ToolResultMessage(
                    toolCallId=tool_call.id,
                    toolName=tool_call.name,
                    content=[TextContent(text=str(result_text))],
                    isError=is_error,
                    timestamp=now,
                )
            )

    return transcript
