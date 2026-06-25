"""YAML frontmatter parsing helpers.

Splits optional Markdown frontmatter from the body while preserving normal
content when no complete frontmatter fence exists.
"""

from __future__ import annotations

from typing import Any


def _normalize_newlines(value: str) -> str:
    return value.replace("\r\n", "\n").replace("\r", "\n")


def _extract_frontmatter(content: str) -> dict[str, str | None]:
    normalized = _normalize_newlines(content)

    if not normalized.startswith("---"):
        return {"yaml_string": None, "body": normalized}

    end_index = normalized.find("\n---", 3)
    if end_index == -1:
        return {"yaml_string": None, "body": normalized}

    return {
        "yaml_string": normalized[4:end_index],
        "body": normalized[end_index + 4:].strip(),
    }


def parse_frontmatter(content: str) -> dict[str, Any]:
    """Parse optional YAML frontmatter from Markdown-like content."""
    extracted = _extract_frontmatter(content)
    yaml_string = extracted["yaml_string"]
    body = extracted["body"]

    if not yaml_string:
        return {"frontmatter": {}, "body": body}

    try:
        import yaml

        parsed = yaml.safe_load(yaml_string)
        if not isinstance(parsed, dict):
            parsed = {}
    except Exception:
        parsed = {}

    return {"frontmatter": parsed, "body": body}


def strip_frontmatter(content: str) -> str:
    """Remove YAML frontmatter from content when a complete frontmatter block exists."""
    return parse_frontmatter(content)["body"]
