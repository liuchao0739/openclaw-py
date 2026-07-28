from __future__ import annotations

import platform

from openclaw.agents.modes.interactive.theme.theme import theme


Keybinding = dict[str, Any]


def _format_key_part(part: str, capitalize: bool = False) -> str:
    display_part = "option" if platform.system() == "Darwin" and part.lower() == "alt" else part
    if capitalize:
        return display_part[0].upper() + display_part[1:]
    return display_part


def _format_key_text(key: str, capitalize: bool = False) -> str:
    return "/".join(
        "+".join(
            _format_key_part(part, capitalize) for part in k.split("+")
        )
        for k in key.split("/")
    )


def _format_keys(keys: list[str], capitalize: bool = False) -> str:
    if not keys:
        return ""
    return _format_key_text("/".join(keys), capitalize)


def key_text(keybinding: Keybinding) -> str:
    keys = keybinding.get("keys", [])
    return _format_keys(keys)


def key_hint(keybinding: Keybinding, description: str) -> str:
    return theme.fg("dim", key_text(keybinding)) + theme.fg("muted", f" {description}")
