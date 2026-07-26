"""Tests for openclaw.tools.planner — mirrors src/tools/planner.test.ts."""

from __future__ import annotations

import pytest

from openclaw.tools.diagnostics import ToolPlanContractError
from openclaw.tools.execution import format_tool_executor_ref
from openclaw.tools.planner import build_tool_plan
from openclaw.tools.protocol import ToolProtocolDescriptor, to_tool_protocol_descriptors
from openclaw.tools.types import ToolDescriptor


def _descriptor(name: str, **overrides: object) -> ToolDescriptor:
    base: ToolDescriptor = {
        "name": name,
        "description": f"{name} description",
        "input_schema": {"type": "object"},
        "owner": {"kind": "core"},
        "executor": {"kind": "core", "executor_id": name},
    }
    base.update(overrides)  # type: ignore[typeddict-item]
    return base


def _expect_hidden_tool(plan: dict[str, list], index: int) -> dict:
    entry = plan["hidden"][index]
    if entry is None:
        raise AssertionError(f"Expected hidden tool at index {index}")
    return entry


class TestBuildToolPlan:
    def test_sorts_visible_and_hidden_tools_deterministically(self) -> None:
        plan = build_tool_plan(
            {
                "descriptors": [
                    _descriptor("zeta"),
                    _descriptor("alpha"),
                    _descriptor(
                        "hidden",
                        sort_key="middle",
                        availability={"kind": "env", "name": "MISSING_ENV"},
                    ),
                ],
                "availability": {"env": {}},
            }
        )

        assert [entry["descriptor"]["name"] for entry in plan["visible"]] == ["alpha", "zeta"]
        assert [entry["descriptor"]["name"] for entry in plan["hidden"]] == ["hidden"]
        assert [
            diagnostic["reason"] for diagnostic in _expect_hidden_tool(plan, 0)["diagnostics"]
        ] == ["env-missing"]

    def test_fails_deterministically_on_duplicate_tool_names(self) -> None:
        with pytest.raises(ToolPlanContractError) as exc_info:
            build_tool_plan({"descriptors": [_descriptor("read"), _descriptor("read")]})

        assert exc_info.value.code == "duplicate-tool-name"
        assert exc_info.value.tool_name == "read"

    def test_fails_closed_when_visible_descriptor_has_no_executor(self) -> None:
        with pytest.raises(ToolPlanContractError) as exc_info:
            build_tool_plan({"descriptors": [_descriptor("read", executor=None)]})

        assert exc_info.value.code == "missing-executor"
        assert exc_info.value.tool_name == "read"

    def test_does_not_require_executor_for_unavailable_descriptors(self) -> None:
        plan = build_tool_plan(
            {
                "descriptors": [
                    _descriptor(
                        "plugin_tool",
                        executor=None,
                        availability={"kind": "plugin-enabled", "plugin_id": "demo"},
                    )
                ],
                "availability": {"enabled_plugin_ids": set()},
            }
        )

        assert plan["visible"] == []
        hidden_tool = _expect_hidden_tool(plan, 0)
        assert hidden_tool["descriptor"]["name"] == "plugin_tool"
        assert [entry["reason"] for entry in hidden_tool["diagnostics"]] == ["plugin-disabled"]

    def test_hides_descriptors_with_malformed_empty_all_of_availability(self) -> None:
        plan = build_tool_plan(
            {"descriptors": [_descriptor("malformed", availability={"all_of": []})]}
        )

        assert plan["visible"] == []
        hidden_tool = _expect_hidden_tool(plan, 0)
        assert hidden_tool["descriptor"]["name"] == "malformed"
        assert hidden_tool["diagnostics"] == [
            {
                "reason": "unsupported-signal",
                "message": "Empty availability allOf group",
            }
        ]

    def test_keeps_protocol_conversion_separate_from_executor_refs(self) -> None:
        plan = build_tool_plan(
            {
                "descriptors": [
                    _descriptor(
                        "plugin_tool",
                        owner={"kind": "plugin", "plugin_id": "demo"},
                        executor={
                            "kind": "plugin",
                            "plugin_id": "demo",
                            "tool_name": "plugin_tool",
                        },
                    )
                ]
            }
        )

        assert format_tool_executor_ref(plan["visible"][0]["executor"]) == "plugin:demo:plugin_tool"
        assert to_tool_protocol_descriptors(plan["visible"]) == [
            ToolProtocolDescriptor(
                name="plugin_tool",
                description="plugin_tool description",
                input_schema={"type": "object"},
            )
        ]
