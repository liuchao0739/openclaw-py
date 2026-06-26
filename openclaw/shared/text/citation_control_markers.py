"""Citation control marker helpers remove unsupported citation control tokens.

Mirrors src/shared/text/citation-control-markers.ts.
"""

from __future__ import annotations

import re

_UNSUPPORTED_CITATION_CONTROL_MARKER_RE = re.compile(r"cite(?:\[[^\]]*\])?", re.IGNORECASE)
_TRAILING_UNSUPPORTED_CITATION_CONTROL_MARKER_RE = re.compile(
    r"[ \t]*cite(?:\[[^\]]*\])?(?=\r?\n|$)", re.IGNORECASE
)


def strip_unsupported_citation_control_markers(text: str) -> str:
    """Remove unsupported model citation-control markers without disturbing normal hard breaks."""
    if not isinstance(text, str):
        return ""
    result = _TRAILING_UNSUPPORTED_CITATION_CONTROL_MARKER_RE.sub("", text)
    result = _UNSUPPORTED_CITATION_CONTROL_MARKER_RE.sub("", result)
    return result
