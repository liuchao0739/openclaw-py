from typing import Any, List, Optional, TypedDict

from .provider_id import normalize_provider_id


def _is_record(value: Any) -> bool:
    return isinstance(value, dict) and not isinstance(value, list)


class ConfiguredModelRef(TypedDict):
    path: str
    value: str


AGENT_MODEL_CONFIG_KEYS: List[str] = [
    "model",
    "imageModel",
    "imageGenerationModel",
    "videoGenerationModel",
    "musicGenerationModel",
    "voiceModel",
    "pdfModel",
]


def collect_configured_model_refs(
    config: Any,
    options: Optional[dict] = None,
) -> List[ConfiguredModelRef]:
    options = options or {}
    refs: List[ConfiguredModelRef] = []

    def push_model_ref(path: str, value: Any) -> None:
        if isinstance(value, str) and value.strip():
            refs.append({"path": path, "value": value.strip()})

    def collect_model_config(path: str, value: Any) -> None:
        if isinstance(value, str):
            push_model_ref(path, value)
            return
        if not _is_record(value):
            return
        push_model_ref(f"{path}.primary", value.get("primary"))
        fallbacks = value.get("fallbacks")
        if isinstance(fallbacks, list):
            for index, entry in enumerate(fallbacks):
                push_model_ref(f"{path}.fallbacks.{index}", entry)

    def collect_from_agent(path: str, agent: Any) -> None:
        if not _is_record(agent):
            return
        for key in AGENT_MODEL_CONFIG_KEYS:
            collect_model_config(f"{path}.{key}", agent.get(key))
        push_model_ref(
            f"{path}.heartbeat.model",
            agent.get("heartbeat", {}).get("model") if _is_record(agent.get("heartbeat")) else None,
        )
        collect_model_config(
            f"{path}.subagents.model",
            agent.get("subagents", {}).get("model") if _is_record(agent.get("subagents")) else None,
        )
        if _is_record(agent.get("compaction")):
            push_model_ref(f"{path}.compaction.model", agent.get("compaction", {}).get("model"))
            memory_flush = agent.get("compaction", {}).get("memoryFlush")
            push_model_ref(
                f"{path}.compaction.memoryFlush.model",
                memory_flush.get("model") if _is_record(memory_flush) else None,
            )
        if _is_record(agent.get("models")):
            for model_ref in agent.get("models", {}).keys():
                push_model_ref(f"{path}.models.{model_ref}", model_ref)

    root = config if _is_record(config) else {}
    agents = root.get("agents") if _is_record(root.get("agents")) else {}
    collect_from_agent("agents.defaults", agents.get("defaults"))
    agents_list = agents.get("list")
    if isinstance(agents_list, list):
        for index, entry in enumerate(agents_list):
            collect_from_agent(f"agents.list.{index}", entry)
    if options.get("includeChannelModelOverrides", True):
        channels = root.get("channels") if _is_record(root.get("channels")) else {}
        model_by_channel = channels.get("modelByChannel") if _is_record(channels.get("modelByChannel")) else {}
        for channel_id, channel_map in model_by_channel.items():
            if not _is_record(channel_map):
                continue
            for target_id, model_ref in channel_map.items():
                push_model_ref(f"channels.modelByChannel.{channel_id}.{target_id}", model_ref)
    hooks = root.get("hooks") if _is_record(root.get("hooks")) else {}
    hooks_mappings = hooks.get("mappings")
    if isinstance(hooks_mappings, list):
        for index, mapping in enumerate(hooks_mappings):
            push_model_ref(
                f"hooks.mappings.{index}.model",
                mapping.get("model") if _is_record(mapping) else None,
            )
    push_model_ref("hooks.gmail.model", hooks.get("gmail", {}).get("model") if _is_record(hooks.get("gmail")) else None)
    messages = root.get("messages")
    messages_tts = messages.get("tts") if _is_record(messages) else None
    push_model_ref(
        "messages.tts.summaryModel",
        messages_tts.get("summaryModel") if _is_record(messages_tts) else None,
    )
    channels = root.get("channels") if _is_record(root.get("channels")) else {}
    channels_discord = channels.get("discord") if _is_record(channels.get("discord")) else None
    channels_discord_voice = channels_discord.get("voice") if _is_record(channels_discord) else None
    push_model_ref(
        "channels.discord.voice.model",
        channels_discord_voice.get("model") if _is_record(channels_discord_voice) else None,
    )
    return refs


def collect_configured_model_ref_values(
    config: Any,
    options: Optional[dict] = None,
) -> List[str]:
    return [ref["value"] for ref in collect_configured_model_refs(config, options)]


def extract_provider_from_model_ref(value: str) -> Optional[str]:
    trimmed = value.strip()
    slash = trimmed.find("/")
    if slash <= 0:
        return None
    return normalize_provider_id(trimmed[:slash])
