"""Agent session hooks (context pruning, compaction safeguard)."""

from openclaw.agents.agent_hooks.compaction_instructions import (
    DEFAULT_COMPACTION_INSTRUCTIONS,
    compose_split_turn_instructions,
    resolve_compaction_instructions,
)
from openclaw.agents.agent_hooks.context_pruning import (  # noqa: F401
    DEFAULT_CONTEXT_PRUNING_SETTINGS,
    compute_effective_settings,
    prune_context_messages,
    register_context_pruning_extension,
)

__all__ = [
    "DEFAULT_COMPACTION_INSTRUCTIONS",
    "DEFAULT_CONTEXT_PRUNING_SETTINGS",
    "compose_split_turn_instructions",
    "compute_effective_settings",
    "prune_context_messages",
    "register_context_pruning_extension",
    "resolve_compaction_instructions",
]