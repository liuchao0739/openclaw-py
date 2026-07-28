from __future__ import annotations

from typing import Any


async def onboard_non_interactive_command(
    opts: dict[str, Any] | None = None,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    options = opts or {}
    provider = options.get("provider", "openclaw")

    if rt.get("log"):
        rt["log"](f"Onboarding provider: {provider}")

    return {
        "ok": True,
        "provider": provider,
        "steps": ["auth", "config", "skills"],
    }
