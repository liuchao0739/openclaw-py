from __future__ import annotations

import os
from typing import Any

from openclaw.plugin_sdk.provider_auth import (
    coerce_secret_ref,
    ensure_auth_profile_store,
    list_profiles_for_provider,
)
from openclaw.plugin_sdk.secret_input_runtime import resolve_required_configured_secret_ref_input_string

PROVIDER_ID = "github-copilot"


async def resolve_first_github_token(params: dict[str, Any]) -> dict[str, str | bool]:
    auth_store = ensure_auth_profile_store(params.get("agentDir"), {"allowKeychainPrompt": False})
    profile_ids = list_profiles_for_provider(auth_store, PROVIDER_ID)
    has_profile = len(profile_ids) > 0
    env = params.get("env", os.environ)
    env_token = env.get("COPILOT_GITHUB_TOKEN", "") or env.get("GH_TOKEN", "") or env.get("GITHUB_TOKEN", "") or ""
    github_token = env_token.strip()
    if github_token or not has_profile:
        return {"githubToken": github_token, "hasProfile": has_profile}

    profile_id = profile_ids[0] if profile_ids else None
    profile = auth_store.profiles.get(profile_id) if profile_id else None
    if not profile or profile.get("type") != "token":
        return {"githubToken": "", "hasProfile": has_profile}
    direct_token = (profile.get("token") or "").strip()
    if direct_token:
        return {"githubToken": direct_token, "hasProfile": has_profile}
    token_ref = coerce_secret_ref(profile.get("tokenRef"))
    if token_ref and token_ref.get("source") == "env" and token_ref.get("id", "").strip():
        env_key = token_ref["id"].strip()
        return {
            "githubToken": (env.get(env_key, "") or os.environ.get(env_key, "")).strip(),
            "hasProfile": has_profile,
        }

    if token_ref and params.get("config"):
        try:
            resolved = await resolve_required_configured_secret_ref_input_string(
                {
                    "config": params["config"],
                    "env": env,
                    "value": profile.get("tokenRef"),
                    "path": f"providers.github-copilot.authProfiles.{profile_id or 'default'}.tokenRef",
                }
            )
            return {
                "githubToken": (resolved or "").strip(),
                "hasProfile": has_profile,
            }
        except Exception:
            return {"githubToken": "", "hasProfile": has_profile}

    return {"githubToken": "", "hasProfile": has_profile}
