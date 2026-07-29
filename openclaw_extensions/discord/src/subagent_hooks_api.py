from typing import Any


def register_discord_subagent_hooks(api: Any) -> None:
    if hasattr(api, "registerSubagentHooks"):
        api.registerSubagentHooks({"channelId": "discord"})
