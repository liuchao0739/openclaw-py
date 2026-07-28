from __future__ import annotations

from typing import Any, Literal, TypeAlias

DIFF_LAYOUTS: tuple[str, ...] = ("unified", "split")
DIFF_MODES: tuple[str, ...] = ("view", "image", "file", "both")
DIFF_THEMES: tuple[str, ...] = ("light", "dark")
DIFF_INDICATORS: tuple[str, ...] = ("bars", "classic", "none")
DIFF_IMAGE_QUALITY_PRESETS: tuple[str, ...] = ("standard", "hq", "print")
DIFF_OUTPUT_FORMATS: tuple[str, ...] = ("png", "pdf")

DiffLayout: TypeAlias = str
DiffMode: TypeAlias = str
DiffTheme: TypeAlias = str
DiffIndicators: TypeAlias = str
DiffImageQualityPreset: TypeAlias = str
DiffOutputFormat: TypeAlias = str
DiffRenderTarget: TypeAlias = str

DiffPresentationDefaults: TypeAlias = dict[str, Any]
DiffFileDefaults: TypeAlias = dict[str, Any]
DiffToolDefaults: TypeAlias = dict[str, Any]
DiffArtifactContext: TypeAlias = dict[str, Any]
DiffArtifactMeta: TypeAlias = dict[str, Any]
DiffInput: TypeAlias = dict[str, Any]
DiffRenderOptions: TypeAlias = dict[str, Any]
DiffViewerOptions: TypeAlias = dict[str, Any]
DiffViewerPayload: TypeAlias = dict[str, Any]
RenderedDiffDocument: TypeAlias = dict[str, Any]

DIFF_ARTIFACT_ID_PATTERN = r"^[0-9a-f]{20}$"
DIFF_ARTIFACT_TOKEN_PATTERN = r"^[0-9a-f]{48}$"