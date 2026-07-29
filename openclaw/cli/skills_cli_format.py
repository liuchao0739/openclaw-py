from __future__ import annotations

from typing import Any


def format_skill_row(skill: dict) -> str:
    name = skill.get("name", "")
    version = skill.get("version", "")
    return f"{name:<30} {version}"


def format_skills_table(skills: list[dict]) -> str:
    if not skills:
        return "No skills found."
    lines = [format_skill_row(s) for s in skills]
    return "
".join(lines)
