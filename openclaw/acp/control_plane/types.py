"""ACP control-plane types."""

from __future__ import annotations

from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, Field


class AcpSessionResolutionKind(StrEnum):
    NONE = "none"
    STALE = "stale"
    READY = "ready"


class SessionAcpMeta(BaseModel):
    backend: str
    agent: str
    session_id: str | None = Field(default=None, alias="sessionId")

    model_config = {"populate_by_name": True, "extra": "allow"}


class AcpSessionResolution(BaseModel):
    kind: AcpSessionResolutionKind
    session_key: str = Field(alias="sessionKey")
    meta: SessionAcpMeta | None = None
    error: str | None = None

    model_config = {"populate_by_name": True}


class AcpInitializeSessionInput(BaseModel):
    session_key: str = Field(alias="sessionKey")
    agent: str
    mode: str = "interactive"
    resume_session_id: str | None = Field(default=None, alias="resumeSessionId")
    cwd: str | None = None
    backend_id: str | None = Field(default=None, alias="backendId")

    model_config = {"populate_by_name": True}


class AcpRunTurnInput(BaseModel):
    session_key: str = Field(alias="sessionKey")
    text: str
    mode: str = "default"
    request_id: str = Field(alias="requestId")

    model_config = {"populate_by_name": True}


class AcpCloseSessionInput(BaseModel):
    session_key: str = Field(alias="sessionKey")
    reason: str
    discard_persistent_state: bool = Field(default=False, alias="discardPersistentState")
    clear_meta: bool = Field(default=False, alias="clearMeta")

    model_config = {"populate_by_name": True}


class AcpCloseSessionResult(BaseModel):
    runtime_closed: bool = Field(alias="runtimeClosed")
    meta_cleared: bool = Field(alias="metaCleared")
    runtime_notice: str | None = Field(default=None, alias="runtimeNotice")

    model_config = {"populate_by_name": True}


class AcpSessionStatus(BaseModel):
    session_key: str = Field(alias="sessionKey")
    backend: str
    agent: str
    state: Literal["idle", "running", "closed"] = "idle"

    model_config = {"populate_by_name": True}


class TurnLatencyStats(BaseModel):
    completed: int = 0
    failed: int = 0
    total_ms: int = Field(default=0, alias="totalMs")
    max_ms: int = Field(default=0, alias="maxMs")

    model_config = {"populate_by_name": True}
