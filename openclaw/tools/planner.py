"""Plans usable tools from descriptors, availability, and request constraints.

Mirrors src/tools/planner.ts.
"""

from __future__ import annotations

from openclaw.tools.availability import evaluate_tool_availability
from openclaw.tools.diagnostics import ToolPlanContractError
from openclaw.tools.types import (
    BuildToolPlanOptions,
    HiddenToolPlanEntry,
    ToolDescriptor,
    ToolPlan,
    ToolPlanEntry,
)


def _assert_unique_names(descriptors: list[ToolDescriptor]) -> None:
    seen: set[str] = set()
    for descriptor in descriptors:
        name = descriptor["name"]
        if name in seen:
            raise ToolPlanContractError(
                code="duplicate-tool-name",
                tool_name=name,
                message=f"Duplicate tool descriptor name: {name}",
            )
        seen.add(name)


def build_tool_plan(options: BuildToolPlanOptions) -> ToolPlan:
    """Build the visible and hidden tool plan for a runtime context."""
    descriptors = sorted(
        options["descriptors"],
        key=lambda descriptor: (
            descriptor.get("sort_key") or descriptor["name"],
            descriptor["name"],
        ),
    )
    _assert_unique_names(descriptors)

    visible: list[ToolPlanEntry] = []
    hidden: list[HiddenToolPlanEntry] = []

    for descriptor in descriptors:
        diagnostics = evaluate_tool_availability(
            descriptor=descriptor,
            context=options.get("availability"),
        )
        if diagnostics:
            hidden.append({"descriptor": descriptor, "diagnostics": diagnostics})
            continue
        executor = descriptor.get("executor")
        if executor is None:
            raise ToolPlanContractError(
                code="missing-executor",
                tool_name=descriptor["name"],
                message=f"Visible tool descriptor has no executor ref: {descriptor['name']}",
            )
        visible.append({"descriptor": descriptor, "executor": executor})

    return {"visible": visible, "hidden": hidden}
