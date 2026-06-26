"""Removes unpaired Unicode surrogate characters from a string.

Mirrors src/llm/utils/sanitize-unicode.ts.

Unpaired surrogates cause JSON serialization errors in many API providers.
Valid emoji and other characters outside the BMP use properly paired surrogates
and will NOT be affected.
"""

from __future__ import annotations

import re

# Match unpaired high surrogates (not followed by low) or unpaired low surrogates
# (not preceded by high).
_UNPAIRED_SURROGATE_RE = re.compile(
    r"[\ud800-\udbff](?![\udc00-\udfff])|(?<![\ud800-\udbff])[\udc00-\udfff]"
)


def sanitize_surrogates(text: str) -> str:
    """Remove unpaired Unicode surrogate characters from a string."""
    if not isinstance(text, str):
        return ""
    return _UNPAIRED_SURROGATE_RE.sub("", text)
