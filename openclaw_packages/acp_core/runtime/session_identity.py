from __future__ import annotations

import time
from typing import Any

from ..normalize_text import normalize_text
from ..types import SessionAcpIdentity, SessionAcpIdentitySource, SessionAcpMeta
from .types import AcpRuntimeHandle, AcpRuntimeStatus


def _normalize_identity_state(value: Any) -> str | None:
    if value not in ("pending", "resolved"):
        return None
    return value


def _normalize_identity_source(value: Any) -> SessionAcpIdentitySource | None:
    if value not in ("ensure", "status", "event"):
        return None
    return value


def _normalize_identity(
    identity: SessionAcpIdentity | None,
) -> SessionAcpIdentity | None:
    if not identity:
        return None
    state = _normalize_identity_state(identity.get("state"))
    source = _normalize_identity_source(identity.get("source"))
    acpx_record_id = normalize_text(identity.get("acpxRecordId"))
    acpx_session_id = normalize_text(identity.get("acpxSessionId"))
    agent_session_id = normalize_text(identity.get("agentSessionId"))
    last_updated_at = identity.get("lastUpdatedAt")
    if isinstance(last_updated_at, bool):
        last_updated_at = None
    if isinstance(last_updated_at, (int, float)):
        import math
        if not math.isfinite(last_updated_at):
            last_updated_at = None
    else:
        last_updated_at = None

    has_any_id = bool(acpx_record_id or acpx_session_id or agent_session_id)
    if not state and not source and not has_any_id and last_updated_at is None:
        return None

    resolved = bool(acpx_session_id or agent_session_id)
    normalized_state = state or ("resolved" if resolved else "pending")

    result: SessionAcpIdentity = {
        "state": normalized_state,
        "source": source or "status",
        "lastUpdatedAt": last_updated_at if last_updated_at is not None else int(time.time() * 1000),
    }
    if acpx_record_id:
        result["acpxRecordId"] = acpx_record_id
    if acpx_session_id:
        result["acpxSessionId"] = acpx_session_id
    if agent_session_id:
        result["agentSessionId"] = agent_session_id
    return result


def _read_identity_ids_from_handle(handle: AcpRuntimeHandle) -> dict[str, str | None]:
    return {
        "acpxRecordId": normalize_text(handle.get("acpxRecordId")),
        "acpxSessionId": normalize_text(handle.get("backendSessionId")),
        "agentSessionId": normalize_text(handle.get("agentSessionId")),
    }


def _build_session_identity(
    acpx_record_id: str | None,
    acpx_session_id: str | None,
    agent_session_id: str | None,
    state: str,
    source: SessionAcpIdentitySource,
    now: int,
) -> SessionAcpIdentity | None:
    if not acpx_record_id and not acpx_session_id and not agent_session_id:
        return None
    result: SessionAcpIdentity = {
        "state": state,
        "source": source,
        "lastUpdatedAt": now,
    }
    if acpx_record_id:
        result["acpxRecordId"] = acpx_record_id
    if acpx_session_id:
        result["acpxSessionId"] = acpx_session_id
    if agent_session_id:
        result["agentSessionId"] = agent_session_id
    return result


def resolve_session_identity_from_meta(
    meta: SessionAcpMeta | None,
) -> SessionAcpIdentity | None:
    if not meta:
        return None
    return _normalize_identity(meta.get("identity"))


def identity_has_stable_session_id(identity: SessionAcpIdentity | None) -> bool:
    return bool(identity and (identity.get("acpxSessionId") or identity.get("agentSessionId")))


def resolve_runtime_resume_session_id(
    identity: SessionAcpIdentity | None,
) -> str | None:
    if not identity:
        return None
    return normalize_text(identity.get("agentSessionId")) or normalize_text(
        identity.get("acpxSessionId")
    )


def is_session_identity_pending(identity: SessionAcpIdentity | None) -> bool:
    if not identity:
        return True
    return identity.get("state") == "pending"


def identity_equals(
    left: SessionAcpIdentity | None,
    right: SessionAcpIdentity | None,
) -> bool:
    a = _normalize_identity(left)
    b = _normalize_identity(right)
    if not a and not b:
        return True
    if not a or not b:
        return False
    return (
        a.get("state") == b.get("state")
        and a.get("acpxRecordId") == b.get("acpxRecordId")
        and a.get("acpxSessionId") == b.get("acpxSessionId")
        and a.get("agentSessionId") == b.get("agentSessionId")
        and a.get("source") == b.get("source")
    )


def merge_session_identity(
    current: SessionAcpIdentity | None,
    incoming: SessionAcpIdentity | None,
    now: int,
) -> SessionAcpIdentity | None:
    a = _normalize_identity(current)
    b = _normalize_identity(incoming)
    if not a:
        if not b:
            return None
        result = dict(b)
        result["lastUpdatedAt"] = now
        return result
    if not b:
        return a

    current_resolved = a.get("state") == "resolved"
    incoming_resolved = b.get("state") == "resolved"
    allow_incoming_value = not current_resolved or incoming_resolved

    next_record_id = (
        b.get("acpxRecordId") if allow_incoming_value and b.get("acpxRecordId") else a.get("acpxRecordId")
    )
    next_acpx_session_id = (
        b.get("acpxSessionId") if allow_incoming_value and b.get("acpxSessionId") else a.get("acpxSessionId")
    )
    next_agent_session_id = (
        b.get("agentSessionId")
        if allow_incoming_value and b.get("agentSessionId")
        else a.get("agentSessionId")
    )

    next_resolved = bool(next_acpx_session_id or next_agent_session_id)
    if next_resolved:
        next_state = "resolved"
    elif current_resolved:
        next_state = "resolved"
    else:
        next_state = b.get("state", "pending")
    next_source = b.get("source") if allow_incoming_value else a.get("source")

    result: SessionAcpIdentity = {
        "state": next_state,
        "source": next_source or "status",
        "lastUpdatedAt": now,
    }
    if next_record_id:
        result["acpxRecordId"] = next_record_id
    if next_acpx_session_id:
        result["acpxSessionId"] = next_acpx_session_id
    if next_agent_session_id:
        result["agentSessionId"] = next_agent_session_id
    return result


def create_identity_from_ensure(
    handle: AcpRuntimeHandle,
    now: int,
) -> SessionAcpIdentity | None:
    ids = _read_identity_ids_from_handle(handle)
    return _build_session_identity(
        ids["acpxRecordId"], ids["acpxSessionId"], ids["agentSessionId"],
        "pending", "ensure", now,
    )


def create_identity_from_handle_event(
    handle: AcpRuntimeHandle,
    now: int,
) -> SessionAcpIdentity | None:
    ids = _read_identity_ids_from_handle(handle)
    state = "resolved" if ids["agentSessionId"] else "pending"
    return _build_session_identity(
        ids["acpxRecordId"], ids["acpxSessionId"], ids["agentSessionId"],
        state, "event", now,
    )


def create_identity_from_status(
    status: AcpRuntimeStatus | None,
    now: int,
) -> SessionAcpIdentity | None:
    if not status:
        return None
    details = status.get("details")
    acpx_record_id = normalize_text(status.get("acpxRecordId")) or normalize_text(
        details.get("acpxRecordId") if details else None
    )
    acpx_session_id = (
        normalize_text(status.get("backendSessionId"))
        or normalize_text(details.get("backendSessionId") if details else None)
        or normalize_text(details.get("acpxSessionId") if details else None)
    )
    agent_session_id = normalize_text(status.get("agentSessionId")) or normalize_text(
        details.get("agentSessionId") if details else None
    )
    if not acpx_record_id and not acpx_session_id and not agent_session_id:
        return None
    resolved = bool(acpx_session_id or agent_session_id)
    result: SessionAcpIdentity = {
        "state": "resolved" if resolved else "pending",
        "source": "status",
        "lastUpdatedAt": now,
    }
    if acpx_record_id:
        result["acpxRecordId"] = acpx_record_id
    if acpx_session_id:
        result["acpxSessionId"] = acpx_session_id
    if agent_session_id:
        result["agentSessionId"] = agent_session_id
    return result


def resolve_runtime_handle_identifiers_from_identity(
    identity: SessionAcpIdentity | None,
) -> dict[str, str]:
    if not identity:
        return {}
    result: dict[str, str] = {}
    if identity.get("acpxSessionId"):
        result["backendSessionId"] = identity["acpxSessionId"]
    if identity.get("agentSessionId"):
        result["agentSessionId"] = identity["agentSessionId"]
    return result