"""Chutes provider plugin entrypoint with OAuth and API-key auth methods."""

from __future__ import annotations

import os
from typing import Any

from openclaw.packages.normalization_core import normalize_optional_string
from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw.plugin_sdk.provider_auth_api_key import create_provider_api_key_auth_method
from openclaw_extensions.chutes.models import CHUTES_DEFAULT_MODEL_REF
from openclaw_extensions.chutes.oauth import login_chutes
from openclaw_extensions.chutes.onboard import (
    apply_chutes_api_key_config,
    apply_chutes_provider_config,
)
from openclaw_extensions.chutes.provider_catalog import (
    build_chutes_provider,
    build_static_chutes_provider,
)

PROVIDER_ID = "chutes"


def _read_string_value(value: Any) -> str | None:
    if isinstance(value, str) and value.strip():
        return value
    return None


def _resolve_oauth_api_key_marker(provider_id: str) -> str:
    return f"oauth:{provider_id.strip()}"


async def _run_chutes_oauth(ctx: dict[str, Any]) -> dict[str, Any]:
    is_remote = bool(ctx.get("isRemote"))
    redirect_uri = (
        (os.environ.get("CHUTES_OAUTH_REDIRECT_URI") or "").strip()
        or "http://127.0.0.1:1456/oauth-callback"
    )
    scopes = (
        (os.environ.get("CHUTES_OAUTH_SCOPES") or "").strip()
        or "openid profile chutes:invoke"
    )

    client_id_env = (os.environ.get("CHUTES_CLIENT_ID") or "").strip()
    if client_id_env:
        client_id = client_id_env
    else:
        prompter = ctx["prompter"]
        client_id = (
            await prompter.text(
                {
                    "message": "Enter Chutes OAuth client id",
                    "placeholder": "cid_xxx",
                    "validate": lambda value: (
                        None if (isinstance(value, str) and value.strip()) else "Required"
                    ),
                }
            )
        ).strip()
    client_secret = normalize_optional_string(os.environ.get("CHUTES_CLIENT_SECRET"))

    prompter = ctx["prompter"]
    if is_remote:
        note_lines = [
            "You are running in a remote/VPS environment.",
            "A URL will be shown for you to open in your LOCAL browser.",
            "After signing in, paste the redirect URL back here.",
            "",
            f"Redirect URI: {redirect_uri}",
        ]
    else:
        note_lines = [
            "Browser will open for Chutes authentication.",
            "If the callback doesn't auto-complete, paste the redirect URL.",
            "",
            f"Redirect URI: {redirect_uri}",
        ]
    await prompter.note("\n".join(note_lines), "Chutes OAuth")

    progress = ctx["prompter"].progress("Starting Chutes OAuth…")
    try:
        oauth = ctx["oauth"]
        handlers = oauth.create_vps_aware_handlers(
            {
                "isRemote": is_remote,
                "prompter": ctx["prompter"],
                "runtime": ctx.get("runtime"),
                "spin": progress,
                "openUrl": ctx.get("openUrl"),
                "localBrowserMessage": "Complete sign-in in browser…",
            }
        )
        on_auth = handlers["onAuth"]
        on_prompt = handlers["onPrompt"]

        creds = await login_chutes(
            {
                "app": {
                    "clientId": client_id,
                    "clientSecret": client_secret,
                    "redirectUri": redirect_uri,
                    "scopes": [scope for scope in scopes.split() if scope],
                },
                "manual": is_remote,
                "onAuth": on_auth,
                "onPrompt": on_prompt,
                "onProgress": lambda message: progress.update(message),
            }
        )

        progress.stop("Chutes OAuth complete")

        credential_extra: dict[str, Any] = {"clientId": client_id}
        account_id = creds.get("accountId")
        if isinstance(account_id, str):
            credential_extra["accountId"] = account_id

        return {
            "providerId": PROVIDER_ID,
            "defaultModel": CHUTES_DEFAULT_MODEL_REF,
            "access": creds.get("access"),
            "refresh": creds.get("refresh"),
            "expires": creds.get("expires"),
            "email": _read_string_value(creds.get("email")),
            "credentialExtra": credential_extra,
            "configPatch": apply_chutes_provider_config({}),
            "notes": [
                "Chutes OAuth tokens auto-refresh. Re-run login if refresh fails or access is revoked.",
                f"Redirect URI: {redirect_uri}",
            ],
        }
    except Exception:
        progress.stop("Chutes OAuth failed")
        await ctx["prompter"].note(
            "\n".join(
                [
                    "Trouble with OAuth?",
                    "Verify CHUTES_CLIENT_ID (and CHUTES_CLIENT_SECRET if required).",
                    f"Verify the OAuth app redirect URI includes: {redirect_uri}",
                    "Chutes docs: https://chutes.ai/docs/sign-in-with-chutes/overview",
                ]
            ),
            "OAuth help",
        )
        raise


async def _resolve_chutes_catalog(ctx: dict[str, Any]) -> dict[str, Any] | None:
    resolve_provider_auth = ctx["resolveProviderAuth"]
    resolved = resolve_provider_auth(
        PROVIDER_ID,
        {"oauthMarker": _resolve_oauth_api_key_marker(PROVIDER_ID)},
    )
    api_key = resolved.get("apiKey")
    discovery_api_key = resolved.get("discoveryApiKey")
    if not api_key:
        return None
    provider = await build_chutes_provider(discovery_api_key)
    provider["apiKey"] = api_key
    return {"provider": provider}


async def _resolve_static_chutes_catalog(_ctx: dict[str, Any]) -> dict[str, Any]:
    return {"provider": build_static_chutes_provider()}


def _register(api: OpenClawPluginApi) -> None:
    api.register_provider(
        {
            "id": PROVIDER_ID,
            "label": "Chutes",
            "docsPath": "/providers/chutes",
            "envVars": ["CHUTES_API_KEY", "CHUTES_OAUTH_TOKEN"],
            "auth": [
                {
                    "id": "oauth",
                    "label": "Chutes OAuth",
                    "hint": "Browser sign-in",
                    "kind": "oauth",
                    "wizard": {
                        "choiceId": "chutes",
                        "choiceLabel": "Chutes (OAuth)",
                        "choiceHint": "Browser sign-in",
                        "groupId": "chutes",
                        "groupLabel": "Chutes",
                        "groupHint": "OAuth + API key",
                    },
                    "run": lambda ctx: _run_chutes_oauth(ctx),
                },
                create_provider_api_key_auth_method(
                    {
                        "providerId": PROVIDER_ID,
                        "methodId": "api-key",
                        "label": "Chutes API key",
                        "hint": "Open-source models including Llama, DeepSeek, and more",
                        "optionKey": "chutesApiKey",
                        "flagName": "--chutes-api-key",
                        "envVar": "CHUTES_API_KEY",
                        "promptMessage": "Enter Chutes API key",
                        "noteTitle": "Chutes",
                        "noteMessage": "\n".join(
                            [
                                "Chutes provides access to leading open-source models including Llama, DeepSeek, and more.",
                                "Get your API key at: https://chutes.ai/settings/api-keys",
                            ]
                        ),
                        "defaultModel": CHUTES_DEFAULT_MODEL_REF,
                        "expectedProviders": ["chutes"],
                        "applyConfig": lambda cfg: apply_chutes_api_key_config(cfg),
                        "wizard": {
                            "choiceId": "chutes-api-key",
                            "choiceLabel": "Chutes API key",
                            "groupId": "chutes",
                            "groupLabel": "Chutes",
                            "groupHint": "OAuth + API key",
                        },
                    }
                ),
            ],
            "catalog": {
                "order": "profile",
                "run": _resolve_chutes_catalog,
            },
            "staticCatalog": {
                "order": "profile",
                "run": _resolve_static_chutes_catalog,
            },
        }
    )


default = define_plugin_entry(
    id=PROVIDER_ID,
    name="Chutes Provider",
    description="Bundled Chutes.ai provider plugin",
    register=_register,
)
