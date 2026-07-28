from __future__ import annotations

from typing import Any

from .._normalization import normalize_lowercase_string_or_empty
from ..normalize_text import normalize_text
from ..types import SessionAcpIdentity, SessionAcpMeta
from .session_identity import (
    is_session_identity_pending,
    resolve_session_identity_from_meta,
)

ACP_SESSION_IDENTITY_RENDERER_VERSION = "v1"
AcpSessionIdentifierRenderMode = str

SessionResumeHintResolver = Any

_ACP_AGENT_RESUME_HINT_BY_KEY: dict[str, SessionResumeHintResolver] = {
    "codex": lambda agentSessionId: f"resume in Codex CLI: `codex resume {agentSessionId}` (continues this conversation).",
    "openai": lambda agentSessionId: f"resume in Codex CLI: `codex resume {agentSessionId}` (continues this conversation).",
    "codex-cli": lambda agentSessionId: f"resume in Codex CLI: `codex resume {agentSessionId}` (continues this conversation).",
    "kimi": lambda agentSessionId: f"resume in Kimi CLI: `kimi resume {agentSessionId}` (continues this conversation).",
    "moonshot-kimi": lambda agentSessionId: f"resume in Kimi CLI: `kimi resume {agentSessionId}` (continues this conversation).",
}


def _normalize_agent_hint_key(value: Any) -> str | None:
    normalized = normalize_text(value)
    if not normalized:
        return None
    return normalize_lowercase_string_or_empty(normalized).replace(" ", "-").replace("_", "-")


def _resolve_acp_agent_resume_hint_line(
    agent_id: str | None = None,
    agent_session_id: str | None = None,
) -> str | None:
    resolved_agent_session_id = normalize_text(agent_session_id)
    agent_key = _normalize_agent_hint_key(agent_id)
    if not resolved_agent_session_id or not agent_key:
        return None
    resolver = _ACP_AGENT_RESUME_HINT_BY_KEY.get(agent_key)
    if resolver is None:
        return None
    return resolver(resolved_agent_session_id)


def resolve_acp_session_identifier_lines(
    session_key: str,
    meta: SessionAcpMeta | None = None,
) -> list[str]:
    backend = normalize_text(meta.get("backend") if meta else None) or "backend"
    identity = resolve_session_identity_from_meta(meta)
    return resolve_acp_session_identifier_lines_from_identity(
        backend=backend,
        identity=identity,
        mode="status",
    )


def resolve_acp_session_identifier_lines_from_identity(
    backend: str,
    identity: SessionAcpIdentity | None = None,
    mode: str = "status",
) -> list[str]:
    resolved_backend = normalize_text(backend) or "backend"
    resolved_mode = mode or "status"
    agent_session_id = normalize_text(identity.get("agentSessionId") if identity else None)
    acpx_session_id = normalize_text(identity.get("acpxSessionId") if identity else None)
    acpx_record_id = normalize_text(identity.get("acpxRecordId") if identity else None)
    has_identifier = bool(agent_session_id or acpx_session_id or acpx_record_id)

    if is_session_identity_pending(identity) and has_identifier:
        if resolved_mode == "status":
            return ["session ids: pending (available after the first reply)"]
        return []

    lines: list[str] = []
    if agent_session_id:
        lines.append(f"agent session id: {agent_session_id}")
    if acpx_session_id:
        lines.append(f"{resolved_backend} session id: {acpx_session_id}")
    if acpx_record_id:
        lines.append(f"{resolved_backend} record id: {acpx_record_id}")
    return lines


def resolve_acp_session_cwd(meta: SessionAcpMeta | None = None) -> str | None:
    runtime_cwd = normalize_text(
        meta.get("runtimeOptions", {}).get("cwd") if meta and meta.get("runtimeOptions") else None
    )
    if runtime_cwd:
        return runtime_cwd
    return normalize_text(meta.get("cwd") if meta else None)


def resolve_acp_thread_session_detail_lines(
    session_key: str,
    meta: SessionAcpMeta | None = None,
) -> list[str]:
    identity = resolve_session_identity_from_meta(meta)
    backend = normalize_text(meta.get("backend") if meta else None) or "backend"
    lines = resolve_acp_session_identifier_lines_from_identity(
        backend=backend,
        identity=identity,
        mode="thread",
    )
    if not lines:
        return lines
    hint = _resolve_acp_agent_resume_hint_line(
        agent_id=meta.get("agent") if meta else None,
        agent_session_id=identity.get("agentSessionId") if identity else None,
    )
    if hint:
        lines.append(hint)
    return lines