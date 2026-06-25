"""Resolves model choices for commitment extraction and follow-up checks."""

from __future__ import annotations

from typing import Any


def resolve_commitment_default_model_ref(
    cfg: dict[str, Any] | None = None,
    agent_id: str | None = None,
) -> dict[str, str]:
    """Resolve the default model for commitment extraction.

    Deferred to agents/model-selection module; returns a default when unavailable.
    """
    try:
        from openclaw.agents.model_selection import resolve_default_model_for_agent

        return resolve_default_model_for_agent({"cfg": cfg or {}, "agentId": agent_id})
    except Exception:
        # Fallback to config defaults
        agents = (cfg or {}).get("agents", {})
        defaults = agents.get("defaults", {}) if isinstance(agents, dict) else {}
        model = defaults.get("model", "gpt-4") if isinstance(defaults, dict) else "gpt-4"
        provider = defaults.get("provider", "openai") if isinstance(defaults, dict) else "openai"
        return {"provider": provider, "model": model}
