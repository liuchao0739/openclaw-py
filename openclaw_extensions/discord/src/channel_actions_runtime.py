from typing import Any, Dict


discord_message_actions = {
    "resolveExecutionMode": lambda ctx: "local",
    "describeMessageTool": lambda ctx: None,
    "extractToolSend": lambda ctx: None,
    "prepareSendPayload": lambda ctx: None,
}


async def handle_discord_message_action(ctx: Dict[str, Any]) -> Dict[str, Any]:
    return {"handled": False}
