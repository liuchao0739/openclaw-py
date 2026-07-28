from __future__ import annotations

from typing import Any


class PluginInstallPolicy:
    ALLOW = "allow"
    DENY = "deny"
    PROMPT = "prompt"


def resolve_install_policy(
    plugin_id: str,
    config: dict[str, Any] | None = None,
) -> str:
    config = config or {}
    policies = config.get("installPolicies", {})
    return policies.get(plugin_id, PluginInstallPolicy.PROMPT)


def check_install_allowed(
    plugin_id: str,
    config: dict[str, Any] | None = None,
) -> bool:
    policy = resolve_install_policy(plugin_id, config)
    return policy != PluginInstallPolicy.DENY
