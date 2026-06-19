"""ACP session manager control plane."""

from __future__ import annotations

from openclaw.acp.control_plane.types import (
    AcpCloseSessionInput,
    AcpCloseSessionResult,
    AcpInitializeSessionInput,
    AcpRunTurnInput,
    AcpSessionResolution,
    AcpSessionResolutionKind,
    AcpSessionStatus,
    SessionAcpMeta,
    TurnLatencyStats,
)


class SessionActorQueue:
    async def run(self, session_key: str, fn):
        return await fn()


class AcpSessionManager:
    """Coordinates ACP session metadata, runtime handles, and turn execution."""

    def __init__(self) -> None:
        self._actor_queue = SessionActorQueue()
        self._sessions: dict[str, SessionAcpMeta] = {}
        self._turn_latency = TurnLatencyStats()

    def resolve_session(self, session_key: str) -> AcpSessionResolution:
        meta = self._sessions.get(session_key)
        if meta is None:
            return AcpSessionResolution(kind=AcpSessionResolutionKind.NONE, sessionKey=session_key)
        return AcpSessionResolution(
            kind=AcpSessionResolutionKind.READY,
            sessionKey=session_key,
            meta=meta,
        )

    async def initialize_session(self, input_data: AcpInitializeSessionInput) -> AcpSessionStatus:
        meta = SessionAcpMeta(
            backend=input_data.backend_id or "default",
            agent=input_data.agent,
            sessionId=input_data.resume_session_id,
        )
        self._sessions[input_data.session_key] = meta
        return AcpSessionStatus(
            sessionKey=input_data.session_key,
            backend=meta.backend,
            agent=meta.agent,
            state="idle",
        )

    async def run_turn(self, input_data: AcpRunTurnInput) -> dict[str, str]:
        resolution = self.resolve_session(input_data.session_key)
        if resolution.kind != AcpSessionResolutionKind.READY:
            raise RuntimeError(f"session not ready: {input_data.session_key}")
        self._turn_latency.completed += 1
        return {"requestId": input_data.request_id, "text": input_data.text}

    async def close_session(self, input_data: AcpCloseSessionInput) -> AcpCloseSessionResult:
        existed = input_data.session_key in self._sessions
        if input_data.clear_meta:
            self._sessions.pop(input_data.session_key, None)
        return AcpCloseSessionResult(
            runtimeClosed=existed,
            metaCleared=input_data.clear_meta and existed,
        )

    def observability_snapshot(self) -> dict[str, object]:
        return {
            "sessions": len(self._sessions),
            "turnLatency": self._turn_latency.model_dump(by_alias=True),
        }
