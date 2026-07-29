from __future__ import annotations

from collections.abc import Callable
from typing import Any, Protocol, TypedDict

from openclaw.llm.core import AssistantMessage, Message, Model, ThinkingLevel, Tool

Api = str


class StreamOptions(TypedDict, total=False):
    temperature: float
    max_tokens: int
    stop: list[str]
    api_key: str
    session_id: str
    prompt_cache_key: str
    headers: dict[str, str]
    timeout_ms: int
    max_retries: int
    max_retry_delay_ms: int
    metadata: dict[str, Any]


class SimpleStreamOptions(StreamOptions, total=False):
    reasoning: ThinkingLevel
    thinking_budgets: dict[str, int]


ProviderStreamOptions = StreamOptions


class Context(TypedDict, total=False):
    system_prompt: str
    messages: list[Message]
    tools: list[Tool]


class AssistantMessageEventStreamContract(Protocol):
    def push(self, event: dict[str, Any]) -> None: ...

    def end(self, result: AssistantMessage | None = None) -> None: ...

    def __aiter__(self) -> Any: ...

    async def result(self) -> AssistantMessage: ...


StreamFunction = Callable[
    [Model, Context, StreamOptions | None],
    AssistantMessageEventStreamContract,
]

ApiStreamFunction = Callable[
    [Model, Context, StreamOptions | None],
    AssistantMessageEventStreamContract,
]

ApiStreamSimpleFunction = Callable[
    [Model, Context, SimpleStreamOptions | None],
    AssistantMessageEventStreamContract,
]


class ApiProvider(TypedDict):
    api: Api
    stream: StreamFunction
    stream_simple: StreamFunction


class ApiProviderInternal(TypedDict):
    api: Api
    stream: ApiStreamFunction
    stream_simple: ApiStreamSimpleFunction


class RegisteredApiProvider(TypedDict, total=False):
    provider: ApiProviderInternal
    source_id: str
