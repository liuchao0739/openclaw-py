"""Agent runtime-plan auth forwarding decisions.

Mirrors src/agents/runtime-plan/auth.ts.
"""

from __future__ import annotations

from typing import Any, Mapping

CODEX_HARNESS_AUTH_PROVIDER = "openai"


def _normalize_optional_agent_runtime_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip().lower()
    return trimmed or None


def _resolve_provider_id_for_auth(
    provider: str,
    config: Any = None,
    workspace_dir: str | None = None,
    metadata_snapshot: Mapping[str, Any] | None = None,
) -> str:
    """Resolve provider ID for auth (simplified — no plugin alias lookup)."""
    return provider


def _resolve_harness_auth_provider(
    harness_id: str | None = None,
    harness_runtime: str | None = None,
) -> str | None:
    """Resolve harness auth provider."""
    hid = _normalize_optional_agent_runtime_id(harness_id)
    runtime = _normalize_optional_agent_runtime_id(harness_runtime)
    if hid == "codex" or runtime == "codex":
        return CODEX_HARNESS_AUTH_PROVIDER
    return None


def build_agent_runtime_auth_plan(
    provider: str,
    auth_profile_provider: str | None = None,
    auth_profile_mode: str | None = None,
    session_auth_profile_id: str | None = None,
    session_auth_profile_candidate_ids: list[str] | None = None,
    config: Mapping[str, Any] | None = None,
    workspace_dir: str | None = None,
    metadata_snapshot: Mapping[str, Any] | None = None,
    provider_auth_aliases_enabled: bool | None = None,
    harness_id: str | None = None,
    harness_runtime: str | None = None,
    allow_harness_auth_profile_forwarding: bool | None = None,
) -> dict[str, Any]:
    """Build the auth forwarding plan for one resolved agent runtime."""
    provider_for_auth = _resolve_provider_id_for_auth(
        provider, config=config, workspace_dir=workspace_dir, metadata_snapshot=metadata_snapshot
    )
    auth_profile_provider_for_auth = _resolve_provider_id_for_auth(
        auth_profile_provider or provider,
        config=config,
        workspace_dir=workspace_dir,
        metadata_snapshot=metadata_snapshot,
    )
    harness_auth_provider = _resolve_harness_auth_provider(harness_id, harness_runtime)
    harness_provider_for_auth = (
        _resolve_provider_id_for_auth(
            harness_auth_provider, config=config, workspace_dir=workspace_dir, metadata_snapshot=metadata_snapshot
        )
        if harness_auth_provider
        else None
    )

    harness_can_forward = (
        allow_harness_auth_profile_forwarding is not False
        and harness_provider_for_auth is not None
        and harness_provider_for_auth == auth_profile_provider_for_auth
    )
    provider_can_forward = (
        not harness_provider_for_auth
        and provider_for_auth == auth_profile_provider_for_auth
    )
    can_forward = provider_can_forward or harness_can_forward

    result: dict[str, Any] = {
        "providerForAuth": provider_for_auth,
        "authProfileProviderForAuth": auth_profile_provider_for_auth,
    }
    if harness_provider_for_auth:
        result["harnessAuthProvider"] = harness_provider_for_auth
    if can_forward and session_auth_profile_id:
        result["forwardedAuthProfileId"] = session_auth_profile_id
    if can_forward and session_auth_profile_candidate_ids:
        result["forwardedAuthProfileCandidateIds"] = session_auth_profile_candidate_ids
    return result
