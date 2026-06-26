"""Strip lightweight markdown formatting from text.

Mirrors src/shared/text/strip-markdown.ts. Preserves readable plain-text
structure for TTS and channel fallbacks.
"""

from __future__ import annotations

import re


def strip_markdown(text: str) -> str:
    """Strip markdown formatting from text."""
    if not isinstance(text, str):
        return ""
    result = text
    # Bold
    result = re.sub(r"\*\*(.+?)\*\*", r"\1", result)
    result = re.sub(r"__(.+?)__", r"\1", result)
    # Italic
    result = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"\1", result)
    # Strikethrough
    result = re.sub(r"~~(.+?)~~", r"\1", result)
    # Headers
    result = re.sub(r"^#{1,6}\s+(.+)$", r"\1", result, flags=re.MULTILINE)
    # Blockquotes
    result = re.sub(r"^>\s?(.*)$", r"\1", result, flags=re.MULTILINE)
    # Horizontal rules
    result = re.sub(r"^[-*_]{3,}$", "", result, flags=re.MULTILINE)
    # Inline code
    result = re.sub(r"`([^`]+)`", r"\1", result)
    # Collapse multiple newlines
    result = re.sub(r"\n{3,}", "\n\n", result)
    return result.strip()
