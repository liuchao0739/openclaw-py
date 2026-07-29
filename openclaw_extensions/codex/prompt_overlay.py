from openclaw.plugin_sdk.provider_model_shared import (
    GPT5_BEHAVIOR_CONTRACT,
    GPT5_HEARTBEAT_PROMPT_OVERLAY,
    resolve_gpt5_system_prompt_contribution,
)

CODEX_GPT5_BEHAVIOR_CONTRACT = GPT5_BEHAVIOR_CONTRACT
CODEX_GPT5_HEARTBEAT_PROMPT_OVERLAY = GPT5_HEARTBEAT_PROMPT_OVERLAY


def resolve_codex_system_prompt_contribution(params):
    return resolve_gpt5_system_prompt_contribution(params)
