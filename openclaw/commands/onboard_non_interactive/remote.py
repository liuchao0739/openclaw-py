"""Remote non-interactive onboarding orchestration.

Writes gateway.remote config without local gateway setup.
"""

from __future__ import annotations

from typing import Any

from openclaw.commands.onboard_non_interactive.config_write import (
    commit_non_interactive_onboard_config,
)


async def run_non_interactive_remote_setup(
    opts: dict[str, Any],
    runtime: dict[str, Any] | None = None,
    base_config: dict[str, Any] | None = None,
    base_hash: str | None = None,
) -> dict[str, Any]:
    """Run non-interactive setup for clients that connect to an existing remote gateway."""
    rt = runtime or {}
    base = base_config or {}
    mode = "remote"

    remote_url = (opts.get("remoteUrl") or "").strip()
    if not remote_url:
        error_fn = rt.get("error", print)
        if error_fn:
            error_fn("Missing --remote-url for remote mode.")
        return {"ok": False, "error": "Missing --remote-url"}

    remote_token = (opts.get("remoteToken") or "").strip() or None

    next_config: dict[str, Any] = {
        **base,
        "gateway": {
            **base.get("gateway", {}),
            "mode": "remote",
            "remote": {
                "url": remote_url,
                **({"token": remote_token} if remote_token else {}),
            },
        },
    }

    # Apply wizard metadata (deferred)
    try:
        from openclaw.commands.onboard_helpers import apply_wizard_metadata

        next_config = apply_wizard_metadata(next_config, {"command": "onboard", "mode": mode})
    except Exception:
        pass

    # Commit config
    committed = await commit_non_interactive_onboard_config(
        next_config=next_config,
        base_config=base,
        base_hash=base_hash,
        reset=opts.get("reset", False),
    )

    auth = "token" if remote_token else "none"
    log_fn = rt.get("log", print)

    if opts.get("json"):
        return {"ok": True, "mode": mode, "remoteUrl": remote_url, "auth": auth}
    if log_fn:
        log_fn(f"Remote gateway: {remote_url}")
        log_fn(f"Auth: {auth}")

    return {"ok": True, "mode": mode, "remoteUrl": remote_url, "auth": auth, "config": committed}
