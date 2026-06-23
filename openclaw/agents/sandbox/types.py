"""Sandbox tool policy types."""

from __future__ import annotations

from typing import Literal, TypedDict


class SandboxToolPolicy(TypedDict, total=False):
    allow: list[str]
    deny: list[str]


class SandboxToolPolicySource(TypedDict):
    source: Literal["agent", "global", "default"]
    key: str


class SandboxToolPolicyResolved(TypedDict):
    allow: list[str]
    deny: list[str]
    sources: dict[str, SandboxToolPolicySource]