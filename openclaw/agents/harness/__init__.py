"""Native agent harness contracts and registry."""

from openclaw.agents.harness.errors import (
    MissingAgentHarnessError,
    is_missing_agent_harness_error,
)
from openclaw.agents.harness.policy import AgentHarnessPolicy, resolve_agent_harness_policy
from openclaw.agents.harness.registry import (
    get_registered_agent_harness,
    list_registered_agent_harnesses,
    register_agent_harness,
    reset_agent_harness_registry_for_tests,
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
    "AgentHarnessResetParams",
    "AgentHarnessResultClassification",
    "AgentHarnessSideQuestionParams",
    "AgentHarnessSideQuestionResult",
    "AgentHarnessSupport",
    "AgentHarnessSupportContext",
    "AgentHarnessPolicy",
    "resolve_agent_harness_policy",
    "MissingAgentHarnessError",
    "RegisteredAgentHarness",
    "get_registered_agent_harness",
    "is_missing_agent_harness_error",
    "list_registered_agent_harnesses",
    "register_agent_harness",
    "reset_agent_harness_registry_for_tests",
]