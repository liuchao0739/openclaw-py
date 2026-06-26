"""Status package — fallback notice state, status types.

Mirrors src/status/. Provides fallback notice state helpers.
"""

from __future__ import annotations

from typing import Any, Mapping


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def _are_runtime_model_refs_equivalent(ref1: str, ref2: str, **_: Any) -> bool:
    """Check if two runtime model refs are equivalent (simple string comparison)."""
    return ref1 == ref2


def resolve_active_fallback_state(
    selected_model_ref: str,
    active_model_ref: str,
    config: Any = None,
    state: Mapping[str, Any] | None = None,
) -> dict[str, Any]:
    """Resolve whether a fallback notice is currently active.

    Persisted fallback notice state is active only when the current selected and
    active runtime refs still match the recorded fallback transition.
    """
    state = state or {}
    selected = _normalize_optional_string(state.get("fallbackNoticeSelectedModel"))
    active = _normalize_optional_string(state.get("fallbackNoticeActiveModel"))
    reason = _normalize_optional_string(state.get("fallbackNoticeReason"))
    fallback_active = (
        not _are_runtime_model_refs_equivalent(selected_model_ref, active_model_ref, config=config)
        and selected == selected_model_ref
        and active == active_model_ref
    )
    return {
        "active": fallback_active,
        "reason": reason if fallback_active else None,
    }
