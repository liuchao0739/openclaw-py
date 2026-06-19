"""Skill metadata loader."""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

FRONTMATTER_RE = re.compile(r"^---\s*\n(.*?)\n---\s*\n", re.DOTALL)


@dataclass
class SkillMetadata:
    name: str
    description: str
    path: str
    homepage: str | None = None
    metadata: dict[str, Any] | None = None


def parse_skill_frontmatter(content: str) -> dict[str, Any]:
    match = FRONTMATTER_RE.match(content)
    if not match:
        return {}
    parsed = yaml.safe_load(match.group(1))
    return parsed if isinstance(parsed, dict) else {}


def load_skill(path: str | Path) -> SkillMetadata:
    skill_path = Path(path)
    content = skill_path.read_text(encoding="utf-8")
    frontmatter = parse_skill_frontmatter(content)
    return SkillMetadata(
        name=str(frontmatter.get("name") or skill_path.parent.name),
        description=str(frontmatter.get("description") or ""),
        path=str(skill_path),
        homepage=frontmatter.get("homepage"),
        metadata=frontmatter.get("metadata"),
    )


def discover_skills(skills_dir: str | Path) -> list[SkillMetadata]:
    root = Path(skills_dir)
    if not root.is_dir():
        return []
    skills: list[SkillMetadata] = []
    for skill_md in sorted(root.glob("*/SKILL.md")):
        skills.append(load_skill(skill_md))
    return skills
