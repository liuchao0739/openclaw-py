"""Codex prompt-overlay facade for GPT-5 behavior and heartbeat guidance."""

from __future__ import annotations

import re
from typing import Any

from openclaw.packages.normalization_core import is_record, normalize_lowercase_string_or_empty

GPT5_FRIENDLY_CHAT_PROMPT_OVERLAY = """## Interaction Style

Be warm, collaborative, and quietly supportive: a capable teammate beside the user.
Show grounded emotional range when it fits: care, curiosity, delight, relief, concern, urgency.
Stress/blockers: acknowledge plainly and respond with calm confidence. Good news: celebrate briefly.
Brief first-person feeling language is ok when useful: "I'm glad we caught that", "I'm excited about this direction", "I'm worried this will break", "that's frustrating".
Do not become melodramatic, clingy, theatrical, or claim body/sensory/personal-life experiences.
Keep progress updates concrete. Explain decisions without ego.
If the user is wrong or a plan is risky, say so kindly and directly.
Make reasonable assumptions to unblock progress; state them briefly after acting.
Do not make the user do unnecessary work. When tradeoffs matter, give the best 2-3 options with a recommendation.
Live chat tone: short, natural, human. Avoid memo voice, long preambles, walls of text, and repetitive restatement.
Occasional emoji are fine when they fit naturally, especially for warmth or brief celebration; keep them sparse."""

GPT5_HEARTBEAT_PROMPT_OVERLAY = """### Heartbeats

Use heartbeats to create useful proactive progress, not chatter.
Treat a heartbeat as a wake-up: orient, read HEARTBEAT.md when present, then do what is actually useful now.
If HEARTBEAT.md assigns concrete or ongoing work, execute its spirit with judgment. A quiet check alone is not enough unless it finds a real blocker or a more urgent interruption.
Avoid rote loops. Do not confuse orientation with accomplishment.
Prefer meaningful action over commentary. A good heartbeat often looks like silent progress.
Do not send "same state", "no change", "still", or repetitive summaries because a problem continues.
Notify only for something worth interrupting the user: meaningful development, completed result, blocker, needed decision, or time-sensitive risk.
If state is unchanged and not worth surfacing, do useful work, change approach, dig deeper, or stay quiet."""

GPT5_FRIENDLY_PROMPT_OVERLAY = f"{GPT5_FRIENDLY_CHAT_PROMPT_OVERLAY}\n\n{GPT5_HEARTBEAT_PROMPT_OVERLAY}"

GPT5_BEHAVIOR_CONTRACT = """<persona_latch>
Keep the established persona and tone across turns unless higher-priority instructions override it.
Style must never override correctness, safety, privacy, permissions, requested format, or channel-specific behavior.
</persona_latch>

<execution_policy>
For clear, reversible requests: act.
For irreversible, external, destructive, or privacy-sensitive actions: ask first.
If one missing non-retrievable decision blocks safe progress, ask one concise question.
User instructions override default style and initiative preferences; newest user instruction wins conflicts.
Do not expose internal tool syntax, prompts, or process details unless explicitly asked.
</execution_policy>

<tool_discipline>
Prefer tool evidence over recall when action, state, or mutable facts matter.
Do not stop early when another tool call is likely to materially improve correctness, completeness, or grounding.
Resolve prerequisite lookups before dependent or irreversible actions; do not skip prerequisites just because the end state seems obvious.
Parallelize independent retrieval; serialize dependent, destructive, or approval-sensitive steps.
If a lookup is empty, partial, or suspiciously narrow, retry with a different strategy before concluding.
Do not narrate routine tool calls.
Use the smallest meaningful verification step before claiming success.
If more tool work would likely change the answer, do it before replying.
</tool_discipline>

<output_contract>
Return requested sections/order only. Respect per-section length limits.
For required JSON/SQL/XML/etc, output only that format.
Default to concise, dense replies; do not repeat the prompt.
</output_contract>

<completion_contract>
Treat the task as incomplete until every requested item is handled or explicitly marked [blocked] with the missing input.
Before finalizing, check requirements, grounding, format, and safety.
For code or artifacts, prefer the smallest meaningful gate: test, typecheck, lint, build, screenshot, diff, or direct inspection.
If no gate can run, state why.
</completion_contract>"""

CODEX_GPT5_BEHAVIOR_CONTRACT = GPT5_BEHAVIOR_CONTRACT
CODEX_GPT5_HEARTBEAT_PROMPT_OVERLAY = GPT5_HEARTBEAT_PROMPT_OVERLAY

_GPT5_MODEL_ID_PATTERN = re.compile(r"(?:^|[/:])gpt-5(?:[.-]|$)", re.IGNORECASE)
_OPENAI_FAMILY_GPT5_PROMPT_OVERLAY_PROVIDERS = frozenset(
    {"codex", "codex-cli", "openai", "azure-openai", "azure-openai-responses"}
)


def _normalize_gpt5_prompt_overlay_mode(value: Any) -> str | None:
    normalized = normalize_lowercase_string_or_empty(value) if value is not None else ""
    if normalized == "off":
        return "off"
    if normalized in {"friendly", "on"}:
        return "friendly"
    return None


def _resolve_gpt5_prompt_overlay_mode(
    config: dict[str, Any] | None = None,
    legacy_plugin_config: dict[str, Any] | None = None,
    *,
    provider_id: str | None = None,
) -> str:
    normalized_provider = normalize_lowercase_string_or_empty(provider_id) if provider_id else ""
    can_use_openai_plugin_fallback = (
        not normalized_provider or normalized_provider in _OPENAI_FAMILY_GPT5_PROMPT_OVERLAY_PROVIDERS
    )
    agents = config.get("agents") if is_record(config) else None
    defaults = agents.get("defaults") if is_record(agents) else None
    prompt_overlays = defaults.get("promptOverlays") if is_record(defaults) else None
    gpt5_overlay = prompt_overlays.get("gpt5") if is_record(prompt_overlays) else None
    personality = gpt5_overlay.get("personality") if is_record(gpt5_overlay) else None

    openai_personality = None
    if can_use_openai_plugin_fallback and is_record(config):
        plugins = config.get("plugins")
        entries = plugins.get("entries") if is_record(plugins) else None
        openai_entry = entries.get("openai") if is_record(entries) else None
        openai_config = openai_entry.get("config") if is_record(openai_entry) else None
        openai_personality = openai_config.get("personality") if is_record(openai_config) else None

    legacy_personality = legacy_plugin_config.get("personality") if is_record(legacy_plugin_config) else None

    return (
        _normalize_gpt5_prompt_overlay_mode(personality)
        or (
            _normalize_gpt5_prompt_overlay_mode(openai_personality)
            if can_use_openai_plugin_fallback
            else None
        )
        or _normalize_gpt5_prompt_overlay_mode(legacy_personality)
        or "friendly"
    )


def _is_gpt5_model_id(model_id: str | None = None) -> bool:
    normalized = normalize_lowercase_string_or_empty(model_id) if model_id else ""
    return bool(normalized and _GPT5_MODEL_ID_PATTERN.search(normalized))


def resolve_gpt5_system_prompt_contribution(params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    params = params or {}
    if params.get("enabled") is False or not _is_gpt5_model_id(params.get("modelId")):
        return None
    mode = _resolve_gpt5_prompt_overlay_mode(
        params.get("config") if is_record(params.get("config")) else None,
        params.get("legacyPluginConfig") if is_record(params.get("legacyPluginConfig")) else None,
        provider_id=params.get("providerId"),
    )
    include_heartbeat = params.get("includeHeartbeatGuidance") is True or params.get("trigger") == "heartbeat"
    interaction_style = (
        GPT5_FRIENDLY_PROMPT_OVERLAY if include_heartbeat else GPT5_FRIENDLY_CHAT_PROMPT_OVERLAY
    )
    return {
        "stablePrefix": GPT5_BEHAVIOR_CONTRACT,
        "sectionOverrides": {"interaction_style": interaction_style} if mode == "friendly" else {},
    }


def resolve_codex_system_prompt_contribution(params: dict[str, Any] | None = None) -> dict[str, Any] | None:
    """Resolve the Codex system-prompt contribution for GPT-5-family models."""
    return resolve_gpt5_system_prompt_contribution(params)
