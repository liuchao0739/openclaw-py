"""Shared text package — markdown stripping, citation markers."""

from .strip_markdown import strip_markdown
from .citation_control_markers import strip_unsupported_citation_control_markers

__all__ = [
    "strip_markdown",
    "strip_unsupported_citation_control_markers",
]
