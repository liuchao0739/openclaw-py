from typing import Any, Dict


async def handle_discord_subagent_delivery_target(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"handled": False}


async def handle_discord_subagent_ended(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"handled": False}


async def handle_discord_subagent_spawning(params: Dict[str, Any]) -> Dict[str, Any]:
    return {"handled": False}
