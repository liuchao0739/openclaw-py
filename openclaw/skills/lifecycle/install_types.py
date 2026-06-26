"""Normalized output returned by skill install flows and command wrappers.

Mirrors src/skills/lifecycle/install-types.ts.
"""

from __future__ import annotations

from typing import TypedDict


class SkillInstallResult(TypedDict, total=False):
    ok: bool
    message: str
    stdout: str
    stderr: str
    code: int | None
    warnings: list[str]
