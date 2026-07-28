from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.types import (
    AuthProfileCredential,
    AuthProfileStore,
)


class OAuthSecretRefPolicyViolation(Exception):
    pass


def _push_violation(
    violations: list[dict[str, str]],
    profile_id: str,
    field: str,
    reason: str,
) -> None:
    violations.append({
        "profileId": profile_id,
        "path": f"profiles.{profile_id}.{field}",
        "reason": reason,
    })


def _has_secret_ref_input(
    value: Any,
    ref_value: Any = None,
    defaults: dict[str, Any] | None = None,
) -> bool:
    if isinstance(value, dict) and "source" in value:
        return True
    if isinstance(ref_value, dict) and "source" in ref_value:
        return True
    return False


def _collect_type_oauth_secret_ref_violations(
    profile_id: str,
    credential: AuthProfileCredential,
    defaults: dict[str, Any] | None,
    violations: list[dict[str, str]],
) -> None:
    if credential.get("type") != "oauth":
        return
    reason = 'SecretRef is not allowed for type="oauth" auth profiles.'
    for field in ("access", "refresh", "token", "tokenRef", "key", "keyRef"):
        if not _has_secret_ref_input(credential.get(field)):
            continue
        _push_violation(violations, profile_id, field, reason)


def _collect_oauth_mode_secret_ref_violations(
    profile_id: str,
    credential: AuthProfileCredential,
    defaults: dict[str, Any] | None,
    configured_mode: str | None,
    violations: list[dict[str, str]],
) -> None:
    if configured_mode != "oauth":
        return
    reason = (
        f'SecretRef is not allowed when auth.profiles.{profile_id}.mode is "oauth".'
    )
    if credential.get("type") == "api_key":
        if _has_secret_ref_input(credential.get("key"), credential.get("keyRef")):
            _push_violation(violations, profile_id, "key", reason)
        return
    if credential.get("type") == "token":
        if _has_secret_ref_input(credential.get("token"), credential.get("tokenRef")):
            _push_violation(violations, profile_id, "token", reason)


def collect_oauth_secret_ref_policy_violations(
    store: AuthProfileStore,
    cfg: dict[str, Any] | None = None,
    profile_ids: list[str] | None = None,
) -> list[dict[str, str]]:
    defaults = (cfg or {}).get("secrets", {}).get("defaults") if cfg else None
    profile_filter = set(profile_ids) if profile_ids else None
    violations: list[dict[str, str]] = []

    for profile_id, credential in store.get("profiles", {}).items():
        if profile_filter and profile_id not in profile_filter:
            continue
        _collect_type_oauth_secret_ref_violations(
            profile_id, credential, defaults, violations
        )
        configured_mode = None
        if cfg:
            configured = (
                cfg.get("auth", {}).get("profiles", {}).get(profile_id, {})
            )
            configured_mode = configured.get("mode") if configured else None
        _collect_oauth_mode_secret_ref_violations(
            profile_id, credential, defaults, configured_mode, violations
        )
    return violations


def assert_no_oauth_secret_ref_policy_violations(
    store: AuthProfileStore,
    cfg: dict[str, Any] | None = None,
    profile_ids: list[str] | None = None,
    context: str | None = None,
) -> None:
    violations = collect_oauth_secret_ref_policy_violations(
        store, cfg, profile_ids
    )
    if not violations:
        return
    lines = [
        f"{context or 'auth-profiles'} policy validation failed: OAuth + SecretRef is not supported.",
    ]
    for v in violations:
        lines.append(f"- {v['path']}: {v['reason']}")
    raise OAuthSecretRefPolicyViolation("\n".join(lines))
