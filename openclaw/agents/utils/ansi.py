"""ANSI escape sequence detection and stripping.

Derived from ansi-regex and strip-ansi (MIT, Sindre Sorhus).
"""

from __future__ import annotations

import re

# Valid string terminator sequences: BEL, ESC\, and 0x9c
_ST = r"(?:\u0007|\u001B\u005C|\u009C)"

# OSC sequences: ESC ] ... ST
_OSC = rf"(?:\u001B\][\s\S]*?{_ST})"

# CSI and related: ESC/C1, optional intermediates, optional params, final byte
_CSI = r"[\u001B\u009B][[()#;?]*(?:\d{1,4}(?:[;:]\d{0,4})*)?[\dA-PR-TZcf-nq-uy=><~]"

_ANSI_REGEX = re.compile(f"{_OSC}|{_CSI}")


def strip_ansi(value: str) -> str:
    """Strip ANSI escape sequences from a string."""
    if not isinstance(value, str):
        raise TypeError(f"Expected a `string`, got `{type(value).__name__}`")

    # Fast path: ANSI codes require ESC (7-bit) or CSI (8-bit) introducer
    if "\u001B" not in value and "\u009B" not in value:
        return value

    return _ANSI_REGEX.sub("", value)
