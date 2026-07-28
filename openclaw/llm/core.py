"""LLM core types (ported subset from packages/llm-core)."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class KnownApi(StrEnum):
    OPENAI_COMPLETIONS = "openai-completions"
    OPENAI_RESPONSES = "openai-responses"
    ANTHROPIC_MESSAGES = "anthropic-messages"
    GOOGLE_GENERATIVE_AI = "google-generative-ai"


ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh", "max"]
ModelThinkingLevel = Literal["off", "minimal", "low", "medium", "high", "xhigh", "max"]
StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]
Transport = Literal["sse", "websocket", "websocket-cached", "auto"]


class TextContent(BaseModel):
    type: Literal["text"] = "text"
    text: str


class ImageContent(BaseModel):
    type: Literal["image"] = "image"
    data: str = ""
    mime_type: str = Field(default="image/png", alias="mimeType")

    model_config = {"populate_by_name": True}


class ToolCall(BaseModel):
    type: Literal["toolCall"] = "toolCall"
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class UsageCost(BaseModel):
    input: float = 0
    output: float = 0
    cache_read: float = Field(default=0, alias="cacheRead")
    cache_write: float = Field(default=0, alias="cacheWrite")
    total: float = 0

    model_config = {"populate_by_name": True}


class Usage(BaseModel):
    input: int = 0
    output: int = 0
    cache_read: int = Field(default=0, alias="cacheRead")
    cache_write: int = Field(default=0, alias="cacheWrite")
    total_tokens: int = Field(default=0, alias="totalTokens")
    cost: UsageCost = Field(default_factory=UsageCost)

    model_config = {"populate_by_name": True}


class UserMessage(BaseModel):
    role: Literal["user"] = "user"
    content: str | list[TextContent]
    timestamp: int


class AssistantMessage(BaseModel):
    role: Literal["assistant"] = "assistant"
    content: list[TextContent | ToolCall]
    api: str
    provider: str
    model: str
    usage: Usage = Field(default_factory=Usage)
    stop_reason: StopReason = Field(alias="stopReason")
    error_message: str | None = Field(default=None, alias="errorMessage")
    timestamp: int

    model_config = {"populate_by_name": True}


class ToolResultMessage(BaseModel):
    role: Literal["toolResult"] = "toolResult"
    tool_call_id: str = Field(alias="toolCallId")
    tool_name: str = Field(alias="toolName")
    content: list[TextContent | ImageContent] = Field(default_factory=list)
    is_error: bool = Field(default=False, alias="isError")
    timestamp: int

    model_config = {"populate_by_name": True}


Message = UserMessage | AssistantMessage | ToolResultMessage


class Tool(BaseModel):
    name: str
    description: str
    parameters: dict[str, Any] = Field(default_factory=dict)


class Model(BaseModel):
    id: str
    name: str
    api: str
    provider: str
    base_url: str = Field(alias="baseUrl")
    reasoning: bool = False
    input: list[Literal["text", "image"]] = Field(default_factory=lambda: ["text"])
    context_window: int = Field(default=128000, alias="contextWindow")
    max_tokens: int = Field(default=8192, alias="maxTokens")

    model_config = {"populate_by_name": True}


class ModelRef(BaseModel):
    provider: str
    model: str

    def as_key(self) -> str:
        return f"{self.provider}/{self.model}"


class Context(BaseModel):
    messages: list[Message] = Field(default_factory=list)
    tools: list[Tool] = Field(default_factory=list)
    system_prompt: str | None = Field(default=None, alias="systemPrompt")

    model_config = {"populate_by_name": True}
