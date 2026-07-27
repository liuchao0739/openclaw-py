"""Collects configured model references from OpenClaw config-shaped objects.

Mirrors packages/model-catalog-core/src/configured-model-refs.ts.
"""

from __future__ import annotations

from typing import TypedDict

from openclaw_packages.normalization_core import is_record

from .provider_id import normalize_provider_id

AGENT_MODEL_CONFIG_KEYS: tuple[str, ...] = (
    "model",
    "imageModel",
    "imageGenerationModel",
    "videoGenerationModel",
    "musicGenerationModel",
    "voiceModel",
    "pdfModel",
)


class ConfiguredModelRef(TypedDict):
    path: str
    value: str


def collect_configured_model_refs(
    config: object,
    *,
    include_channel_model_overrides: bool = True,
) -> list[ConfiguredModelRef]:
    refs: list[ConfiguredModelRef] = []

    def push_model_ref(path: str, value: object) -> None:
        if isinstance(value, str) and value.strip():
            refs.append({"path": path, "value": value.strip()})

    def collect_model_config(path: str, value: object) -> None:
        if isinstance(value, str):
            push_model_ref(path, value)
            return
        if not is_record(value):
            return
        push_model_ref(f"{path}.primary", value.get("primary"))
        fallbacks = value.get("fallbacks")
        if isinstance(fallbacks, list):
            for index, entry in enumerate(fallbacks):
                push_model_ref(f"{path}.fallbacks.{index}", entry)

    def collect_from_agent(path: str, agent: object) -> None:
        if not is_record(agent):
            return
        for key in AGENT_MODEL_CONFIG_KEYS:
            collect_model_config(f"{path}.{key}", agent.get(key))
        heartbeat = agent.get("heartbeat")
        push_model_ref(
            f"{path}.heartbeat.model",
            heartbeat.get("model") if is_record(heartbeat) else None,
        )
        subagents = agent.get("subagents")
        collect_model_config(
            f"{path}.subagents.model",
            subagents.get("model") if is_record(subagents) else None,
        )
        compaction = agent.get("compaction")
        if is_record(compaction):
            push_model_ref(f"{path}.compaction.model", compaction.get("model"))
            memory_flush = compaction.get("memoryFlush")
            push_model_ref(
                f"{path}.compaction.memoryFlush.model",
                memory_flush.get("model") if is_record(memory_flush) else None,
            )
        models = agent.get("models")
        if is_record(models):
            for model_ref in models:
                push_model_ref(f"{path}.models.{model_ref}", model_ref)

    root = config if is_record(config) else {}
    agents = root.get("agents")
    agents = agents if is_record(agents) else {}
    collect_from_agent("agents.defaults", agents.get("defaults"))
    agent_list = agents.get("list")
    if isinstance(agent_list, list):
        for index, entry in enumerate(agent_list):
            collect_from_agent(f"agents.list.{index}", entry)
    if include_channel_model_overrides:
        channels = root.get("channels")
        channels = channels if is_record(channels) else {}
        model_by_channel = channels.get("modelByChannel")
        model_by_channel = model_by_channel if is_record(model_by_channel) else {}
        for channel_id, channel_map in model_by_channel.items():
            if not is_record(channel_map):
                continue
            for target_id, model_ref in channel_map.items():
                push_model_ref(
                    f"channels.modelByChannel.{channel_id}.{target_id}",
                    model_ref,
                )
    hooks = root.get("hooks")
    hooks = hooks if is_record(hooks) else {}
    mappings = hooks.get("mappings")
    if isinstance(mappings, list):
        for index, mapping in enumerate(mappings):
            push_model_ref(
                f"hooks.mappings.{index}.model",
                mapping.get("model") if is_record(mapping) else None,
            )
    gmail = hooks.get("gmail")
    push_model_ref("hooks.gmail.model", gmail.get("model") if is_record(gmail) else None)
    messages = root.get("messages")
    tts = messages.get("tts") if is_record(messages) else None
    push_model_ref(
        "messages.tts.summaryModel",
        tts.get("summaryModel") if is_record(tts) else None,
    )
    channels = root.get("channels")
    discord = channels.get("discord") if is_record(channels) else None
    voice = discord.get("voice") if is_record(discord) else None
    push_model_ref(
        "channels.discord.voice.model",
        voice.get("model") if is_record(voice) else None,
    )
    return refs


def collect_configured_model_ref_values(
    config: object,
    *,
    include_channel_model_overrides: bool = True,
) -> list[str]:
    return [
        ref["value"]
        for ref in collect_configured_model_refs(
            config,
            include_channel_model_overrides=include_channel_model_overrides,
        )
    ]


def extract_provider_from_model_ref(value: str) -> str | None:
    trimmed = value.strip()
    slash = trimmed.find("/")
    if slash <= 0:
        return None
    return normalize_provider_id(trimmed[:slash])


__all__ = [
    "AGENT_MODEL_CONFIG_KEYS",
    "ConfiguredModelRef",
    "collect_configured_model_ref_values",
    "collect_configured_model_refs",
    "extract_provider_from_model_ref",
]
