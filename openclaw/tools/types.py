"""Public descriptor contracts for the generic OpenClaw tool planner.

Mirrors src/tools/types.ts.
"""

from __future__ import annotations

from collections.abc import Callable, Mapping, Sequence
from typing import Any, Literal, TypedDict

JsonPrimitive = str | int | float | bool | None
JsonValue = JsonPrimitive | Sequence[Any] | Mapping[str, Any]
JsonObject = dict[str, Any]

ToolUnavailableReason = Literal[
    "auth-missing",
    "config-missing",
    "context-mismatch",
    "env-missing",
    "plugin-disabled",
    "unsupported-signal",
]


class ToolOwnerRefCore(TypedDict):
    kind: Literal["core"]


class ToolOwnerRefPlugin(TypedDict):
    kind: Literal["plugin"]
    plugin_id: str


class ToolOwnerRefChannel(TypedDict, total=False):
    kind: Literal["channel"]
    channel_id: str
    plugin_id: str


class ToolOwnerRefMcp(TypedDict):
    kind: Literal["mcp"]
    server_id: str


ToolOwnerRef = ToolOwnerRefCore | ToolOwnerRefPlugin | ToolOwnerRefChannel | ToolOwnerRefMcp


class ToolExecutorRefCore(TypedDict):
    kind: Literal["core"]
    executor_id: str


class ToolExecutorRefPlugin(TypedDict):
    kind: Literal["plugin"]
    plugin_id: str
    tool_name: str


class ToolExecutorRefChannel(TypedDict):
    kind: Literal["channel"]
    channel_id: str
    action_id: str


class ToolExecutorRefMcp(TypedDict):
    kind: Literal["mcp"]
    server_id: str
    tool_name: str


ToolExecutorRef = (
    ToolExecutorRefCore | ToolExecutorRefPlugin | ToolExecutorRefChannel | ToolExecutorRefMcp
)


class ToolAvailabilitySignalAlways(TypedDict):
    kind: Literal["always"]


class ToolAvailabilitySignalAuth(TypedDict):
    kind: Literal["auth"]
    provider_id: str


class ToolAvailabilitySignalConfig(TypedDict, total=False):
    kind: Literal["config"]
    path: Sequence[str]
    check: Literal["exists", "non-empty", "available"]


class ToolAvailabilitySignalEnv(TypedDict):
    kind: Literal["env"]
    name: str


class ToolAvailabilitySignalPluginEnabled(TypedDict):
    kind: Literal["plugin-enabled"]
    plugin_id: str


class ToolAvailabilitySignalContext(TypedDict, total=False):
    kind: Literal["context"]
    key: str
    equals: JsonPrimitive


ToolAvailabilitySignal = (
    ToolAvailabilitySignalAlways
    | ToolAvailabilitySignalAuth
    | ToolAvailabilitySignalConfig
    | ToolAvailabilitySignalEnv
    | ToolAvailabilitySignalPluginEnabled
    | ToolAvailabilitySignalContext
)


class ToolAvailabilityExpressionAllOf(TypedDict):
    all_of: Sequence[ToolAvailabilityExpression]


class ToolAvailabilityExpressionAnyOf(TypedDict):
    any_of: Sequence[ToolAvailabilityExpression]


ToolAvailabilityExpression = (
    ToolAvailabilitySignal | ToolAvailabilityExpressionAllOf | ToolAvailabilityExpressionAnyOf
)


class ToolDescriptor(TypedDict, total=False):
    name: str
    title: str
    description: str
    input_schema: JsonObject
    output_schema: JsonObject
    owner: ToolOwnerRef
    executor: ToolExecutorRef
    availability: ToolAvailabilityExpression
    annotations: JsonObject
    sort_key: str


class IsConfigValueAvailableParams(TypedDict):
    value: JsonValue
    path: Sequence[str]
    signal: ToolAvailabilitySignalConfig


IsConfigValueAvailable = Callable[[IsConfigValueAvailableParams], bool]


class ToolAvailabilityContext(TypedDict, total=False):
    auth_provider_ids: set[str]
    config: JsonObject
    is_config_value_available: IsConfigValueAvailable
    env: Mapping[str, str | None]
    enabled_plugin_ids: set[str]
    values: Mapping[str, JsonPrimitive | None]


class ToolAvailabilityDiagnostic(TypedDict, total=False):
    reason: ToolUnavailableReason
    signal: ToolAvailabilitySignal
    message: str


class ToolPlanEntry(TypedDict):
    descriptor: ToolDescriptor
    executor: ToolExecutorRef


class HiddenToolPlanEntry(TypedDict):
    descriptor: ToolDescriptor
    diagnostics: Sequence[ToolAvailabilityDiagnostic]


class ToolPlan(TypedDict):
    visible: list[ToolPlanEntry]
    hidden: list[HiddenToolPlanEntry]


class BuildToolPlanOptions(TypedDict, total=False):
    descriptors: Sequence[ToolDescriptor]
    availability: ToolAvailabilityContext
