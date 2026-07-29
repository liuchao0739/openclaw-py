from typing import Any, Dict, Optional


def resolve_discord_group_require_mention(account: Any) -> bool:
    config = account.config if hasattr(account, "config") else account
    group_policy = config.get("groupPolicy") if isinstance(config, dict) else None
    if isinstance(group_policy, dict):
        return bool(group_policy.get("requireMention", False))
    return False


def resolve_discord_group_tool_policy(account: Any) -> Optional[Dict[str, Any]]:
    config = account.config if hasattr(account, "config") else account
    group_policy = config.get("groupPolicy") if isinstance(config, dict) else None
    if isinstance(group_policy, dict):
        return group_policy.get("toolPolicy")
    return None
