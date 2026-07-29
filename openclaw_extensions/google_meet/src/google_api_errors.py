"""Google Meet plugin module implements google api errors behavior."""

from __future__ import annotations

from typing import Any

from openclaw.plugin_sdk.provider_web_search import read_response_text_limited

REAUTH_HINT = "Re-run `openclaw googlemeet auth login` and store the refreshed oauth block."
GOOGLE_API_ERROR_BODY_LIMIT_BYTES = 8 * 1024


def _scope_text(scopes: list[str]) -> str:
    return ", ".join(f"`{scope}`" for scope in scopes)


async def read_google_api_error_detail(response: Any) -> str:
    return await read_response_text_limited(response, GOOGLE_API_ERROR_BODY_LIMIT_BYTES)


async def google_api_error(params: dict[str, Any]) -> Exception:
    detail = await read_google_api_error_detail(params["response"])
    scopes = params.get("scopes") or []
    scope_hint = (
        f" Required OAuth scope: {_scope_text(scopes)}. {REAUTH_HINT}"
        if scopes
        else ""
    )
    status = getattr(params["response"], "status", 0)
    return Exception(f"{params['prefix']} failed ({status}): {detail}{scope_hint}")
