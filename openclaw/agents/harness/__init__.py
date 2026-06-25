"""Native agent harness contracts, registry, selection, and lifecycle."""

from openclaw.agents.harness.agent_end_side_effects import (
    await_agent_end_side_effects,
    run_agent_end_side_effects,
)
from openclaw.agents.harness.builtin_openclaw import create_openclaw_agent_harness
from openclaw.agents.harness.compaction import maybe_compact_agent_harness_session
from openclaw.agents.harness.compaction_recovery import (
    is_recoverable_native_harness_binding_failure,
    is_recoverable_native_harness_binding_reason,
)
from openclaw.agents.harness.context_engine_lifecycle import (
    assemble_harness_context_engine,
    bootstrap_harness_context_engine,
    finalize_harness_context_engine_turn,
    is_active_harness_context_engine,
    run_harness_context_engine_maintenance,
)
from openclaw.agents.harness.errors import (
    MissingAgentHarnessError,
    is_missing_agent_harness_error,
)
from openclaw.agents.harness.hook_context import (
    AgentHarnessHookContext,
    build_agent_hook_context,
)
from openclaw.agents.harness.hook_helpers import (
    run_agent_harness_after_tool_call_hook,
    run_agent_harness_before_message_write_hook,
)
from openclaw.agents.harness.hook_history import (
    MAX_AGENT_HOOK_HISTORY_MESSAGES,
    build_agent_hook_conversation_messages,
    limit_agent_hook_history_messages,
)
from openclaw.agents.harness.lifecycle import run_agent_harness_lifecycle_attempt
from openclaw.agents.harness.lifecycle_hook_helpers import (
    await_agent_harness_agent_end_hook,
    clear_agent_harness_finalize_retry_budget,
    get_agent_harness_hook_runner,
    run_agent_harness_agent_end_hook,
    run_agent_harness_before_agent_finalize_hook,
    run_agent_harness_llm_input_hook,
    run_agent_harness_llm_output_hook,
)
from openclaw.agents.harness.policy import AgentHarnessPolicy, resolve_agent_harness_policy
from openclaw.agents.harness.prompt_compaction_hook_helpers import (
    resolve_agent_harness_before_prompt_build_result,
    run_agent_harness_after_compaction_hook,
    run_agent_harness_before_compaction_hook,
)
from openclaw.agents.harness.registry import (
    clear_agent_harnesses,
    get_agent_harness,
    get_registered_agent_harness,
    list_agent_harness_ids,
    list_registered_agent_harnesses,
    register_agent_harness,
    reset_agent_harness_registry_for_tests,
    restore_registered_agent_harnesses,
)
from openclaw.agents.harness.result_classification import (
    apply_agent_harness_result_classification,
)
from openclaw.agents.harness.runtime_plugin import ensure_selected_agent_harness_plugin
from openclaw.agents.harness.selection import (
    resolve_available_agent_harness_policy,
    resolve_plugin_harness_policy_tools_allow,
    run_agent_harness_attempt,
    select_agent_harness,
)
from openclaw.agents.harness.tool_result_middleware import (
    create_agent_tool_result_middleware_runner,
    is_valid_middleware_content_block,
    is_valid_middleware_details,
    is_valid_middleware_tool_result,
)
from openclaw.agents.harness.types import (
    AgentHarness,
    AgentHarnessAttemptParams,
    AgentHarnessAttemptResult,
    AgentHarnessCompactParams,
    AgentHarnessCompactResult,
    AgentHarnessDeliveryDefaults,
    AgentHarnessResetParams,
    AgentHarnessResultClassification,
    AgentHarnessSideQuestionParams,
    AgentHarnessSideQuestionResult,
    AgentHarnessSupport,
    AgentHarnessSupportContext,
    RegisteredAgentHarness,
)

__all__ = [
    "AgentHarness",
    "AgentHarnessAttemptParams",
    "AgentHarnessAttemptResult",
    "AgentHarnessCompactParams",
    "AgentHarnessCompactResult",
    "AgentHarnessDeliveryDefaults",
    "AgentHarnessHookContext",
    "AgentHarnessPolicy",
    "AgentHarnessResetParams",
    "AgentHarnessResultClassification",
    "AgentHarnessSideQuestionParams",
    "AgentHarnessSideQuestionResult",
    "AgentHarnessSupport",
    "AgentHarnessSupportContext",
    "MAX_AGENT_HOOK_HISTORY_MESSAGES",
    "MissingAgentHarnessError",
    "RegisteredAgentHarness",
    "apply_agent_harness_result_classification",
    "assemble_harness_context_engine",
    "await_agent_end_side_effects",
    "await_agent_harness_agent_end_hook",
    "bootstrap_harness_context_engine",
    "build_agent_hook_conversation_messages",
    "build_agent_hook_context",
    "clear_agent_harness_finalize_retry_budget",
    "clear_agent_harnesses",
    "create_agent_tool_result_middleware_runner",
    "create_openclaw_agent_harness",
    "ensure_selected_agent_harness_plugin",
    "finalize_harness_context_engine_turn",
    "get_agent_harness",
    "get_agent_harness_hook_runner",
    "get_registered_agent_harness",
    "is_active_harness_context_engine",
    "is_missing_agent_harness_error",
    "is_recoverable_native_harness_binding_failure",
    "is_recoverable_native_harness_binding_reason",
    "is_valid_middleware_content_block",
    "is_valid_middleware_details",
    "is_valid_middleware_tool_result",
    "limit_agent_hook_history_messages",
    "list_agent_harness_ids",
    "list_registered_agent_harnesses",
    "maybe_compact_agent_harness_session",
    "register_agent_harness",
    "reset_agent_harness_registry_for_tests",
    "resolve_agent_harness_before_prompt_build_result",
    "resolve_agent_harness_policy",
    "resolve_available_agent_harness_policy",
    "resolve_plugin_harness_policy_tools_allow",
    "restore_registered_agent_harnesses",
    "run_agent_end_side_effects",
    "run_agent_harness_after_compaction_hook",
    "run_agent_harness_after_tool_call_hook",
    "run_agent_harness_agent_end_hook",
    "run_agent_harness_attempt",
    "run_agent_harness_before_agent_finalize_hook",
    "run_agent_harness_before_compaction_hook",
    "run_agent_harness_before_message_write_hook",
    "run_agent_harness_lifecycle_attempt",
    "run_agent_harness_llm_input_hook",
    "run_agent_harness_llm_output_hook",
    "run_harness_context_engine_maintenance",
    "select_agent_harness",
]
