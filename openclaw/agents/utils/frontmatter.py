"""YAML frontmatter parsing helpers.

Mirrors src/agents/utils/frontmatter.ts.
"""

from __future__ import annotations

import re
from typing import Any

import yaml


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _extract_frontmatter(content: str) -> tuple[str | None, str]:
    normalized = _normalize_newlines(content)
    if not normalized.startswith("---"):
        return (None, normalized)
    end_index = normalized.find("\n---", 3)
    if end_index == -1:
        return (None, normalized)
    yaml_string = normalized[4:end_index]
    body = normalized[end_index + 4 :].strip()
    return (yaml_string, body)


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse optional YAML frontmatter from Markdown-like content."""
    yaml_string, body = _extract_frontmatter(content)
    if not yaml_string:
        return {"frontmatter": {}, "body": body}
    try:
        parsed = yaml.safe_load(yaml_string)
    except yaml.YAMLError:
        parsed = {}
    return {"frontmatter": parsed if isinstance(parsed, dict) else {}, "body": body}


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content when a complete frontmatter block exists."""
    return parse_frontmatter(content)["body"]
