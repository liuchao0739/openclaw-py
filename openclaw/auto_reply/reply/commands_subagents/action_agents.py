"""Agents action — list registered agent harnesses."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.reply.commands_subagents.shared import stop_with_text


def handle_agents_action(
    params: dict[str, Any],
    runs: list[dict[str, Any]],
    rest_tokens: list[str],
) -> dict[str, Any]:
    """Handle the /agents command to list registered agent harnesses."""
    try:
        from openclaw.agents.harness.registry import list_registered_agent_harnesses

        harnesses = list_registered_agent_harnesses()
    except Exception:
        harnesses = []

    if not harnesses:
        return stop_with_text("No agent harnesses registered.")

    lines: list[str] = ["🤖 Registered Agent Harnesses:", ""]

    for entry in harnesses:
        harness = entry.get("harness", {})
        harness_id = getattr(harness, "id", entry.get("harness", {}).get("id", "unknown"))
        label = getattr(harness, "label", entry.get("harness", {}).get("label", ""))
        plugin_id = entry.get("ownerPluginId", "")
        line = f"  • {harness_id}"
        if label:
            line += f" — {label}"
        if plugin_id:
            line += f" (plugin: {plugin_id})"
        lines.append(line)

    return stop_with_text("\n".join(lines))
