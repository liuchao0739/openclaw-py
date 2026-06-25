"""Content block type definitions for agent messages."""

from __future__ import annotations

from typing import Any, Literal, TypedDict


class TextContentBlock(TypedDict):
    type: Literal["text"]
    text: str


class ImageContentBlock(TypedDict, total=False):
    type: Literal["image"]
    mimeType: str
    data: str


class ToolCallBlock(TypedDict, total=False):
    type: Literal["toolCall"]
    name: str
    arguments: Any
    toolCallId: str


class ToolResultBlock(TypedDict, total=False):
    type: Literal["toolResult"]
    toolCallId: str
    content: list[Any]
    isError: bool


class ThinkingBlock(TypedDict, total=False):
    type: Literal["thinking"]
    thinking: str


ContentBlock = Any  # Union of all block types above
