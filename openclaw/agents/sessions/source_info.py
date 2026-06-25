"""Source metadata helpers for session resources.

Tracks where prompts, skills, and extension-provided assets came from for diagnostics and UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict

SourceScope = Literal["user", "project", "temporary"]
SourceOrigin = Literal["package", "top-level"]


class SourceInfo(TypedDict, total=False):
    path: str
    source: str
    scope: SourceScope
    origin: SourceOrigin
    baseDir: str | None


class PathMetadata(TypedDict, total=False):
    source: str
    scope: SourceScope
    origin: SourceOrigin
    baseDir: str | None


def create_source_info(path: str, metadata: PathMetadata) -> SourceInfo:
    """Convert package-manager path metadata into the session source-info shape."""
    return SourceInfo(
        path=path,
        source=metadata.get("source", "unknown"),
        scope=metadata.get("scope", "temporary"),
        origin=metadata.get("origin", "top-level"),
        baseDir=metadata.get("baseDir"),
    )


def create_synthetic_source_info(
    path: str,
    options: dict[str, Any] | None = None,
) -> SourceInfo:
    """Build source metadata for generated or synthetic session entries."""
    from typing import Any

    options = options or {}
    return SourceInfo(
        path=path,
        source=options.get("source", "temporary"),
        scope=options.get("scope", "temporary"),
        origin=options.get("origin", "top-level"),
        baseDir=options.get("baseDir"),
    )
