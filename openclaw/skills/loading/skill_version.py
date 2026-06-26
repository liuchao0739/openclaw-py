"""Skill prompt versions are deterministic content markers for model-visible skill catalogs.

Mirrors src/skills/loading/skill-version.ts.
"""

from __future__ import annotations

import hashlib


def compute_skill_prompt_version(content: str) -> str:
    """Compute a deterministic prompt version from skill content."""
    digest = hashlib.sha256(content.encode("utf-8")).hexdigest()[:16]
    return f"sha256:{digest}"
