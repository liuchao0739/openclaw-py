"""Syntax highlighting helpers.

Deferred until a syntax highlighting library is integrated.
"""

from __future__ import annotations

from typing import Any


def highlight(code: str, language: str | None = None) -> str:
    """Apply syntax highlighting. Deferred implementation returns input unchanged."""
    del language
    return code


def detect_language(filename: str, content: str = "") -> str | None:
    """Detect the programming language from a filename."""
    import os

    ext_map = {
        ".py": "python",
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".jsx": "jsx",
        ".json": "json",
        ".yaml": "yaml",
        ".yml": "yaml",
        ".md": "markdown",
        ".rs": "rust",
        ".go": "go",
        ".java": "java",
        ".c": "c",
        ".cpp": "cpp",
        ".h": "c",
        ".sh": "bash",
        ".sql": "sql",
        ".html": "html",
        ".css": "css",
        ".toml": "toml",
        ".xml": "xml",
    }
    _, ext = os.path.splitext(filename)
    return ext_map.get(ext.lower())
