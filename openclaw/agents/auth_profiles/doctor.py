from __future__ import annotations

from typing import Any


class AuthProfileDoctorIssue:
    MISSING_PROVIDER = "missing_provider"
    INVALID_CREDENTIAL = "invalid_credential"
    EXPIRED_TOKEN = "expired_token"
    BROKEN_REF = "broken_ref"
    DUPLICATE_PROFILE = "duplicate_profile"


def run_auth_profile_doctor(
    store: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    store = store or {}
    issues: list[dict[str, Any]] = []

    profiles = store.get("profiles", {})
    for profile_id, credential in profiles.items():
        if not credential.get("provider"):
            issues.append({
                "type": AuthProfileDoctorIssue.MISSING_PROVIDER,
                "profileId": profile_id,
                "message": f"Profile '{profile_id}' missing provider",
            })
        cred_type = credential.get("type")
        if cred_type not in ("api_key", "token", "oauth"):
            issues.append({
                "type": AuthProfileDoctorIssue.INVALID_CREDENTIAL,
                "profileId": profile_id,
                "message": f"Profile '{profile_id}' has invalid credential type: {cred_type}",
            })

    return issues
