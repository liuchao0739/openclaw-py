from __future__ import annotations

from typing import Any


def _build_skill_selection_prompt(skills: list[dict[str, Any]]) -> str:
    if not skills:
        return "No skills found for this provider."
    lines = ["Select skills to migrate:"]
    for i, skill in enumerate(skills, 1):
        lines.append(f"  {i}. {skill.get('name', 'unknown')} - {skill.get('description', '')}")
    lines.append(f"\nEnter skill numbers (comma-separated, or 'all'):")
    return "\n".join(lines)


def select_skills_interactive(
    skills: list[dict[str, Any]],
    runtime: dict[str, Any] | None = None,
) -> list[dict[str, Any]]:
    rt = runtime or {}
    if rt.get("log"):
        rt["log"](_build_skill_selection_prompt(skills))
    return []


def parse_skill_selection(
    selection: str,
    skills: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if selection.strip().lower() == "all":
        return skills
    selected: list[dict[str, Any]] = []
    for part in selection.split(","):
        part = part.strip()
        if not part:
            continue
        try:
            idx = int(part) - 1
            if 0 <= idx < len(skills):
                selected.append(skills[idx])
        except ValueError:
            pass
    return selected
