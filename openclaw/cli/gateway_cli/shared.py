"""Shared gateway CLI helpers for supervised-service stop guidance."""

from __future__ import annotations

import platform
from typing import Any


def render_gateway_service_stop_hints(env: dict[str, str] | None = None) -> list[str]:
    """Render platform-specific service stop hints."""
    import os

    env_map = env or dict(os.environ)
    profile = env_map.get("OPENCLAW_PROFILE", "")
    plat = platform.system().lower()

    hints = ["Tip: openclaw gateway stop"]

    if plat == "darwin":
        label = f"ai.openclaw.gateway{f'.{profile}' if profile else ''}"
        hints.append(f"Or: launchctl bootout gui/$UID/{label}")
    elif plat == "linux":
        service_name = f"openclaw-gateway{f'-{profile}' if profile else ''}"
        hints.append(f"Or: systemctl --user stop {service_name}.service")
    elif plat == "windows":
        task_name = f"OpenClawGateway{f'-{profile}' if profile else ''}"
        hints.append(f'Or: schtasks /End /TN "{task_name}"')

    return hints


async def maybe_explain_gateway_service_stop() -> str | None:
    """Check if a managed gateway service is running and return stop guidance.

    Returns the guidance message if the service appears loaded, None otherwise.
    """
    try:
        from openclaw.daemon.service import resolve_gateway_service

        service = resolve_gateway_service()
        loaded = await service.is_loaded()
    except Exception:
        loaded = None

    if loaded is False:
        return None

    hints = render_gateway_service_stop_hints()
    if loaded:
        msg = "Gateway service appears loaded. Stop it first."
    else:
        msg = "Gateway service status unknown; if supervised, stop it first."

    return msg + "\n" + "\n".join(hints)
