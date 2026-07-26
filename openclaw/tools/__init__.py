"""Tools package — descriptor planning, availability, and protocol conversion."""

from openclaw.tools.availability import evaluate_tool_availability
from openclaw.tools.descriptors import define_tool_descriptor, define_tool_descriptors
from openclaw.tools.diagnostics import ToolPlanContractError, ToolPlanContractErrorCode
from openclaw.tools.execution import format_tool_executor_ref
from openclaw.tools.planner import build_tool_plan
from openclaw.tools.protocol import (
    ToolProtocolDescriptor,
    to_tool_protocol_descriptor,
    to_tool_protocol_descriptors,
)
from openclaw.tools.types import (
    BuildToolPlanOptions,
    HiddenToolPlanEntry,
    JsonObject,
    JsonPrimitive,
    JsonValue,
    ToolAvailabilityContext,
    ToolAvailabilityDiagnostic,
    ToolAvailabilityExpression,
    ToolAvailabilitySignal,
    ToolDescriptor,
    ToolExecutorRef,
    ToolOwnerRef,
    ToolPlan,
    ToolPlanEntry,
    ToolUnavailableReason,
)

__all__ = [
    "BuildToolPlanOptions",
    "HiddenToolPlanEntry",
    "JsonObject",
    "JsonPrimitive",
    "JsonValue",
    "ToolAvailabilityContext",
    "ToolAvailabilityDiagnostic",
    "ToolAvailabilityExpression",
    "ToolAvailabilitySignal",
    "ToolDescriptor",
    "ToolExecutorRef",
    "ToolOwnerRef",
    "ToolPlan",
    "ToolPlanContractError",
    "ToolPlanContractErrorCode",
    "ToolPlanEntry",
    "ToolProtocolDescriptor",
    "ToolUnavailableReason",
    "build_tool_plan",
    "define_tool_descriptor",
    "define_tool_descriptors",
    "evaluate_tool_availability",
    "format_tool_executor_ref",
    "to_tool_protocol_descriptor",
    "to_tool_protocol_descriptors",
]
