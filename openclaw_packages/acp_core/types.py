from __future__ import annotations

from typing import Any, Literal, TypedDict

from ._normalization import normalize_optional_lowercase_string

ACP_PROVENANCE_MODE_VALUES = ["off", "meta", "meta+receipt"]

SessionId = str
AcpProvenanceMode = Literal["off", "meta", "meta+receipt"]


def normalize_acp_provenance_mode(value: str | None) -> AcpProvenanceMode | None:
    normalized = normalize_optional_lowercase_string(value)
    if not normalized:
        return None
    return normalized if normalized in ACP_PROVENANCE_MODE_VALUES else None


class AcpSession(TypedDict):
    sessionId: SessionId
    sessionKey: str
    ledgerSessionId: str | None
    cwd: str
    createdAt: int
    lastTouchedAt: int
    abortController: Any | None
    activeRunId: str | None


class _AcpSessionRateLimit(TypedDict, total=False):
    maxRequests: int | None
    windowMs: int | None


class AcpServerOptions(TypedDict, total=False):
    gatewayUrl: str | None
    gatewayToken: str | None
    gatewayPassword: str | None
    defaultSessionKey: str | None
    defaultSessionLabel: str | None
    requireExistingSession: bool | None
    resetSession: bool | None
    prefixCwd: bool | None
    provenanceMode: AcpProvenanceMode | None
    sessionCreateRateLimit: _AcpSessionRateLimit | None
    verbose: bool | None


SessionAcpIdentitySource = Literal["ensure", "status", "event"]
SessionAcpIdentityState = Literal["pending", "resolved"]


class SessionAcpIdentity(TypedDict, total=False):
    state: SessionAcpIdentityState
    acpxRecordId: str | None
    acpxSessionId: str | None
    agentSessionId: str | None
    source: SessionAcpIdentitySource
    lastUpdatedAt: int


class AcpSessionRuntimeOptions(TypedDict, total=False):
    runtimeMode: str | None
    model: str | None
    thinking: str | None
    cwd: str | None
    permissionProfile: str | None
    timeoutSeconds: int | None
    backendExtras: dict[str, str] | None


class SessionAcpMeta(TypedDict, total=False):
    backend: str
    agent: str
    runtimeSessionName: str
    identity: SessionAcpIdentity | None
    mode: Literal["persistent", "oneshot"]
    runtimeOptions: AcpSessionRuntimeOptions | None
    cwd: str | None
    state: Literal["idle", "running", "error"]
    lastActivityAt: int
    lastError: str | None