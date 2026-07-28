from __future__ import annotations

from openclaw.plugin_sdk.group_agent_runtime import (
    create_agent_group_config_resolver,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

_google_chat_group_config_resolver = create_agent_group_config_resolver({
    "channel": "googlechat",
    "extractSpaceKey": lambda params: (
        normalize_optional_string(params.get("chat", {}).get("key"))
        or normalize_optional_string(params.get("chatId"))
    ),
    "extractSpaceId": lambda params: (
        normalize_optional_string(params.get("chat", {}).get("id"))
        or normalize_optional_string(params.get("chatId"))
    ),
})


def resolve_google_chat_group_config(params: dict) -> dict:
    return _google_chat_group_config_resolver(params)


def _extract_agent_name(agent: dict) -> str:
    return (
        normalize_optional_string(agent.get("name"))
        or normalize_optional_string(agent.get("id"))
        or "agent"
    )


def _extract_agent_description(agent: dict) -> str | None:
    return normalize_optional_string(agent.get("description"))


def _extract_agent_instructions(agent: dict) -> str | None:
    return normalize_optional_string(agent.get("instructions"))


def build_google_chat_agent_list_for_space_resolution(params: dict) -> list[dict]:
    agents = params.get("agents", [])
    result = []
    for agent in agents:
        name = _extract_agent_name(agent)
        description = _extract_agent_description(agent)
        instructions = _extract_agent_instructions(agent)
        snippet = normalize_optional_string(agent.get("snippet"))
        result.append({
            "id": agent.get("id"),
            "name": name,
            "description": description,
            "instructions": instructions,
            "snippet": snippet,
            "capabilities": agent.get("capabilities", []),
        })
    return result


__all__ = [
    "resolve_google_chat_group_config",
    "build_google_chat_agent_list_for_space_resolution",
]