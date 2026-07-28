from __future__ import annotations

from .harness_types import Skill


def _dirname_env_path(path: str) -> str:
    normalized = path.rstrip("/")
    slash_index = normalized.rfind("/")
    return "/" if slash_index <= 0 else normalized[:slash_index]


def format_skill_invocation(skill: Skill, additional_instructions: str | None = None) -> str:
    skill_block = (
        f'<skill name="{skill.name}" location="{skill.filePath}">\n'
        f'References are relative to {_dirname_env_path(skill.filePath)}.\n\n'
        f"{skill.content}\n</skill>"
    )
    if additional_instructions:
        return f"{skill_block}\n\n{additional_instructions}"
    return skill_block
