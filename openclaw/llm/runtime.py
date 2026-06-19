"""LLM runtime request builders."""

from __future__ import annotations

from typing import Any

from openclaw.llm.core import AssistantMessage, Message, Model, TextContent, Tool, UserMessage


def build_openai_chat_completion_request(
    model: Model,
    messages: list[Message],
    *,
    tools: list[Tool] | None = None,
    temperature: float | None = None,
    max_tokens: int | None = None,
) -> dict[str, Any]:
    """Build an OpenAI-compatible chat completion payload."""
    payload_messages: list[dict[str, Any]] = []
    for message in messages:
        if isinstance(message, UserMessage):
            if isinstance(message.content, str):
                payload_messages.append({"role": "user", "content": message.content})
            else:
                payload_messages.append(
                    {
                        "role": "user",
                        "content": [{"type": "text", "text": block.text} for block in message.content],
                    }
                )
        elif isinstance(message, AssistantMessage):
            text_parts = [block.text for block in message.content if isinstance(block, TextContent)]
            payload_messages.append({"role": "assistant", "content": "\n".join(text_parts)})

    body: dict[str, Any] = {
        "model": model.id,
        "messages": payload_messages,
    }
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if tools:
        body["tools"] = [
            {
                "type": "function",
                "function": {
                    "name": tool.name,
                    "description": tool.description,
                    "parameters": tool.parameters,
                },
            }
            for tool in tools
        ]
    return body


def assistant_text_message(model: Model, text: str, *, timestamp: int) -> AssistantMessage:
    return AssistantMessage(
        api=model.api,
        provider=model.provider,
        model=model.id,
        content=[TextContent(text=text)],
        stopReason="stop",
        timestamp=timestamp,
    )
