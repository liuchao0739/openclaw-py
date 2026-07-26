"""Provider API-key auth method helpers for plugin SDK consumers.

Mirrors src/plugin-sdk/provider-auth-api-key.ts exports used by bundled providers.
"""

from __future__ import annotations

from typing import Any


def create_provider_api_key_auth_method(params: dict[str, Any]) -> dict[str, Any]:
    """Create a provider auth method descriptor for API-key credentials."""

    async def run(_ctx: dict[str, Any]) -> dict[str, Any]:
        raise NotImplementedError(
            f"Interactive API-key auth is not implemented for provider {params['providerId']}"
        )

    async def run_non_interactive(_ctx: dict[str, Any]) -> dict[str, Any] | None:
        raise NotImplementedError(
            f"Non-interactive API-key auth is not implemented for provider {params['providerId']}"
        )

    method: dict[str, Any] = {
        "id": params["methodId"],
        "label": params["label"],
        "kind": "api_key",
        "run": run,
        "runNonInteractive": run_non_interactive,
    }
    if params.get("hint") is not None:
        method["hint"] = params["hint"]
    if params.get("wizard") is not None:
        method["wizard"] = params["wizard"]
    return method
