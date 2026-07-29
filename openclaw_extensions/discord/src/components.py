import re
from typing import Any, Dict, List, Optional


DISCORD_COMPONENT_CUSTOM_ID_KEY = "oc.comp"
DISCORD_MODAL_CUSTOM_ID_KEY = "oc.modal"
DISCORD_COMPONENT_ATTACHMENT_PREFIX = "oc.att"


class DiscordFormModal:
    def __init__(self, title: str, fields: List[Dict[str, Any]]):
        self.title = title
        self.fields = fields


def build_discord_component_custom_id(payload: Dict[str, Any]) -> str:
    import json

    return f"{DISCORD_COMPONENT_CUSTOM_ID_KEY}:{json.dumps(payload, separators=(',', ':'))}"


def parse_discord_component_custom_id(custom_id: str) -> Optional[Dict[str, Any]]:
    import json

    if not custom_id or not custom_id.startswith(f"{DISCORD_COMPONENT_CUSTOM_ID_KEY}:"):
        return None
    payload = custom_id[len(DISCORD_COMPONENT_CUSTOM_ID_KEY) + 1:]
    try:
        return json.loads(payload)
    except Exception:
        return None


def parse_discord_component_custom_id_for_interaction(custom_id: str) -> Optional[Dict[str, Any]]:
    return parse_discord_component_custom_id(custom_id)


def build_discord_modal_custom_id(payload: Dict[str, Any]) -> str:
    import json

    return f"{DISCORD_MODAL_CUSTOM_ID_KEY}:{json.dumps(payload, separators=(',', ':'))}"


def parse_discord_modal_custom_id(custom_id: str) -> Optional[Dict[str, Any]]:
    import json

    if not custom_id or not custom_id.startswith(f"{DISCORD_MODAL_CUSTOM_ID_KEY}:"):
        return None
    payload = custom_id[len(DISCORD_MODAL_CUSTOM_ID_KEY) + 1:]
    try:
        return json.loads(payload)
    except Exception:
        return None


def parse_discord_modal_custom_id_for_interaction(custom_id: str) -> Optional[Dict[str, Any]]:
    return parse_discord_modal_custom_id(custom_id)


def build_discord_component_message_flags(params: Dict[str, Any]) -> int:
    flags = 0
    if params.get("suppressEmbeds"):
        flags |= 1 << 2
    if params.get("ephemeral"):
        flags |= 1 << 6
    return flags


def build_discord_interactive_components(spec: Dict[str, Any]) -> List[Dict[str, Any]]:
    components = spec.get("components") or []
    return list(components)


def build_discord_component_message(spec: Dict[str, Any]) -> Dict[str, Any]:
    message: Dict[str, Any] = {"content": spec.get("content", "")}
    if spec.get("components"):
        message["components"] = build_discord_interactive_components(spec)
    if spec.get("embeds"):
        message["embeds"] = spec["embeds"]
    if spec.get("flags") is not None:
        message["flags"] = spec["flags"]
    return message


def create_discord_form_modal(spec: Dict[str, Any]) -> DiscordFormModal:
    return DiscordFormModal(
        title=spec.get("title", ""),
        fields=spec.get("fields", []),
    )


def format_discord_component_event_text(event: Dict[str, Any]) -> str:
    return event.get("text", "")


def read_discord_component_spec(payload: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    return payload.get("components")


def resolve_discord_component_attachment_name(name: str) -> str:
    if name.startswith(DISCORD_COMPONENT_ATTACHMENT_PREFIX):
        return name
    return f"{DISCORD_COMPONENT_ATTACHMENT_PREFIX}:{name}"
