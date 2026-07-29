from __future__ import annotations

from typing import Any, TypedDict


class PluginInstallPlan(TypedDict, total=False):
    name: str
    version: str
    source: str
    steps: list[str]


def build_plugin_install_plan(params: dict) -> PluginInstallPlan:
    return {"name": params.get("name", ""), "version": params.get("version", ""), "source": params.get("source", ""), "steps": []}


def validate_install_plan(plan: dict) -> bool:
    return bool(plan.get("name"))
