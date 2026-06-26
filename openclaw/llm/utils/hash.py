"""Fast deterministic hash to shorten long strings.

Mirrors src/llm/utils/hash.ts. Uses the same cyrb53-inspired algorithm.
"""

from __future__ import annotations

_MASK32 = 0xFFFFFFFF


def _imul(a: int, b: int) -> int:
    """Emulate JavaScript Math.imul (32-bit signed multiply)."""
    a = a & _MASK32
    b = b & _MASK32
    result = (a * b) & _MASK32
    return result


def short_hash(s: str) -> str:
    """Produce a short deterministic hash from a string."""
    h1 = 0xDEADBEEF
    h2 = 0x41C6CE57
    for ch in s:
        c = ord(ch)
        h1 = _imul(h1 ^ c, 2654435761)
        h2 = _imul(h2 ^ c, 1597334677)
    h1 = _imul(h1 ^ (h1 >> 16), 2246822507) ^ _imul(h2 ^ (h2 >> 13), 3266489909)
    h2 = _imul(h2 ^ (h2 >> 16), 2246822507) ^ _imul(h1 ^ (h1 >> 13), 3266489909)
    return f"{h2 & _MASK32:x}" + f"{h1 & _MASK32:x}"
