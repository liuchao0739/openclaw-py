from __future__ import annotations


def mask_api_key(value: str) -> str:
    trimmed = value.strip()
    if not trimmed:
        return "missing"
    if len(trimmed) <= 6:
        return f"{trimmed[:1]}...{trimmed[-1:]}"
    if len(trimmed) <= 16:
        return f"{trimmed[:2]}...{trimmed[-2:]}"
    return f"{trimmed[:8]}...{trimmed[-8:]}"
