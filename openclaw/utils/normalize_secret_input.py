"""Secret normalization for copy/pasted credentials."""

from __future__ import annotations


def normalize_secret_input(value: object) -> str:
    if not isinstance(value, str):
        return ""
    collapsed = value.replace("\r", "").replace("\n", "").replace("\u2028", "").replace("\u2029", "")
    chars: list[str] = []
    for char in collapsed:
        cp = ord(char)
        if cp <= 0xFF:
            chars.append(char)
    return "".join(chars).strip()


def normalize_optional_secret_input(value: object) -> str | None:
    normalized = normalize_secret_input(value)
    return normalized if normalized else None