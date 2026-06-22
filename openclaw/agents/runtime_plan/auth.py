"""Auth forwarding decisions for prepared runtime plans."""

from __future__ import annotations

from typing import Any

from openclaw.agents.runtime_plan.types import AgentRuntimeAuthPlan

CODEX_HARNESS_AUTH_PROVIDER = "openai"


def _normalize_optional_agent_runtime_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _resolve_provider_id_for_auth(
    provider: str,
    *,
    provider_auth_aliases_enabled: bool,
    alias_resolver: Any | None = None,
    alias_lookup: dict[str, Any] | None = None,
) -> str:
    if not provider_auth_aliases_enabled or alias_resolver is None:
        return provider.strip()
    if alias_lookup is None:
        return provider.strip()
    resolved = alias_resolver(provider, alias_lookup)
    return str(resolved).strip() if resolved else provider.strip()


def _resolve_harness_auth_provider(
    *,
    harness_id: str | None = None,
    harness_runtime: str | None = None,
) -> str | None:
    hid = _normalize_optional_agent_runtime_id(harness_id)
    runtime = _normalize_optional_agent_runtime_id(harness_runtime)
    if hid == "codex" or runtime == "codex":
        return CODEX_HARNESS_AUTH_PROVIDER
    return None


def build_agent_runtime_auth_plan(
    *,
    provider: str,
    auth_profile_provider: str | None = None,
    auth_profile_mode: str | None = None,
    session_auth_profile_id: str | None = None,
    session_auth_profile_candidate_ids: list[str] | None = None,
    config: dict[str, Any] | None = None,
    workspace_dir: str | None = None,
    metadata_snapshot: dict[str, Any] | None = None,
    provider_auth_aliases_enabled: bool | None = None,
    harness_id: str | None = None,
    harness_runtime: str | None = None,
    allow_harness_auth_profile_forwarding: bool = True,
    alias_resolver: Any | None = None,
) -> AgentRuntimeAuthPlan:
    del auth_profile_mode, config, workspace_dir, metadata_snapshot

    aliases_enabled = True if provider_auth_aliases_enabled is None else provider_auth_aliases_enabled
    lookup: dict[str, Any] = {}
    provider_for_auth = _resolve_provider_id_for_auth(
        provider,
        provider_auth_aliases_enabled=aliases_enabled,
        alias_resolver=alias_resolver,
        alias_lookup=lookup,
    )
    auth_profile_provider_for_auth = _resolve_provider_id_for_auth(
        auth_profile_provider or provider,
        provider_auth_aliases_enabled=aliases_enabled,
        alias_resolver=alias_resolver,
        alias_lookup=lookup,
    )
    harness_auth = _resolve_harness_auth_provider(
        harness_id=harness_id,
        harness_runtime=harness_runtime,
    )
    harness_provider_for_auth: str | None = None
    if harness_auth:
        harness_provider_for_auth = _resolve_provider_id_for_auth(
            harness_auth,
            provider_auth_aliases_enabled=aliases_enabled,
            alias_resolver=alias_resolver,
            alias_lookup=lookup,
        )

    harness_can_forward = (
        allow_harness_auth_profile_forwarding
        and harness_provider_for_auth is not None
        and harness_provider_for_auth == auth_profile_provider_for_auth
    )
    provider_can_forward = (
        harness_provider_for_auth is None and provider_for_auth == auth_profile_provider_for_auth
    )
    can_forward = provider_can_forward or harness_can_forward

    plan: AgentRuntimeAuthPlan = {
        "providerForAuth": provider_for_auth,
        "authProfileProviderForAuth": auth_profile_provider_for_auth,
    }
    if harness_provider_for_auth:
        plan["harnessAuthProvider"] = harness_provider_for_auth
    if can_forward and session_auth_profile_id:
        plan["forwardedAuthProfileId"] = session_auth_profile_id
    if can_forward and session_auth_profile_candidate_ids:
        plan["forwardedAuthProfileCandidateIds"] = list(session_auth_profile_candidate_ids)
    return plan