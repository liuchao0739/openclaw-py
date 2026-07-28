from __future__ import annotations

from typing import Any

try:
    from diffs_themes import PIERRE_DARK_THEME, PIERRE_LIGHT_THEME
except ImportError:
    PIERRE_DARK_THEME = {}
    PIERRE_LIGHT_THEME = {}

_registered_custom_themes: dict[str, Any] = {}
_resolved_themes: dict[str, Any] = {}
_resolving_themes: dict[str, Any] = {}


def _create_theme_loader(theme_name: str, theme_data: dict[str, Any]):
    cached_theme: dict[str, Any] | None = None

    async def _loader() -> dict[str, Any]:
        nonlocal cached_theme
        if cached_theme is not None:
            return cached_theme
        cached_theme = {**theme_data, "name": theme_name}
        return cached_theme

    return _loader


_PIERRE_THEME_LOADERS = {
    "pierre-dark": _create_theme_loader("pierre-dark", PIERRE_DARK_THEME),
    "pierre-light": _create_theme_loader("pierre-light", PIERRE_LIGHT_THEME),
}


def ensure_pierre_themes_registered() -> None:
    replaced = False
    for theme_name, loader in _PIERRE_THEME_LOADERS.items():
        if _registered_custom_themes.get(theme_name) != loader:
            _registered_custom_themes[theme_name] = loader
            replaced = True
    if not replaced:
        return
    for theme_name in _PIERRE_THEME_LOADERS:
        _resolved_themes.pop(theme_name, None)
        _resolving_themes.pop(theme_name, None)