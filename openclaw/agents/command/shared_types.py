"""Shared command types for public and runtime modules."""

from __future__ import annotations

from typing import Any, TypedDict


class AgentStreamParams(TypedDict, total=False):
    temperature: float
    topP: float
    maxTokens: int
    stop: list[str]
    fastMode: bool
    responseFormat: dict[str, Any]
    frequencyPenalty: float
    presencePenalty: float
    seed: int


class ClientToolFunction(TypedDict, total=False):
    name: str
    description: str
    parameters: dict[str, Any]
    strict: bool


class ClientToolDefinition(TypedDict):
    type: str
    function: ClientToolFunction