from __future__ import annotations

import json
from typing import Any

from openclaw.plugin_sdk.provider_auth import build_copilot_ide_headers


async def fetch_copilot_usage(
    token: str,
    timeout_ms: int,
    fetch_fn: Any = None,
) -> dict[str, Any]:
    import urllib.request

    url = "https://api.github.com/copilot_internal/user"
    headers = {
        "Authorization": f"token {token}",
    }
    headers.update(build_copilot_ide_headers({"includeApiVersion": True}))

    try:
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=timeout_ms / 1000) as res:
            if res.status != 200:
                return {
                    "provider": "github-copilot",
                    "displayName": "GitHub Copilot",
                    "windows": [],
                }
            body = res.read().decode("utf-8")
            data = json.loads(body)

        windows: list[dict[str, Any]] = []
        quota = data.get("quota_snapshots", {})
        if isinstance(quota, dict):
            premium = quota.get("premium_interactions")
            if isinstance(premium, dict):
                remaining = premium.get("percent_remaining")
                if remaining is not None:
                    used = max(0, min(100, 100 - float(remaining or 0)))
                    windows.append({"label": "Premium", "usedPercent": used})
            chat = quota.get("chat")
            if isinstance(chat, dict):
                remaining = chat.get("percent_remaining")
                if remaining is not None:
                    used = max(0, min(100, 100 - float(remaining or 0)))
                    windows.append({"label": "Chat", "usedPercent": used})

        return {
            "provider": "github-copilot",
            "displayName": "GitHub Copilot",
            "windows": windows,
            "plan": data.get("copilot_plan"),
        }
    except Exception:
        return {
            "provider": "github-copilot",
            "displayName": "GitHub Copilot",
            "windows": [],
        }
