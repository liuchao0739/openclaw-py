"""Skill execution stub."""

from __future__ import annotations

from collections.abc import Callable

from openclaw.skills.loader import SkillMetadata

SkillHandler = Callable[[SkillMetadata, str], str]


class SkillExecutor:
    def __init__(self) -> None:
        self._handlers: dict[str, SkillHandler] = {}

    def register(self, skill_name: str, handler: SkillHandler) -> None:
        self._handlers[skill_name] = handler

    def execute(self, skill: SkillMetadata, prompt: str) -> str:
        handler = self._handlers.get(skill.name)
        if handler is None:
            return f"skill '{skill.name}' is registered but has no handler"
        return handler(skill, prompt)
