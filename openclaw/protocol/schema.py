"""Gateway protocol message schemas (MVP subset)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from openclaw.protocol.client_info import GatewayClientInfo
from openclaw.protocol.version import PROTOCOL_VERSION


class HelloRequest(BaseModel):
    type: Literal["hello"] = "hello"
    protocol_version: int = Field(default=PROTOCOL_VERSION, alias="protocolVersion")
    client: GatewayClientInfo

    model_config = {"populate_by_name": True}


class HelloResponse(BaseModel):
    type: Literal["hello-ok"] = "hello-ok"
    protocol_version: int = Field(default=PROTOCOL_VERSION, alias="protocolVersion")
    server_version: str = Field(alias="serverVersion")

    model_config = {"populate_by_name": True}


class ChatMessage(BaseModel):
    role: Literal["user", "assistant", "system", "tool"]
    content: str | list[dict[str, Any]]


class ChatRequest(BaseModel):
    messages: list[ChatMessage]
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}


class ChatResponse(BaseModel):
    message: ChatMessage
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True}
