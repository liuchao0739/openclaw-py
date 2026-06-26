"""Legacy context engine — safe fallback implementation."""

from typing import Any


class LegacyContextEngine:
    """Minimal fallback context engine.

    The legacy engine does no advanced context assembly; it simply returns the
    raw session messages as-is. This keeps behavior parity with the original
    TypeScript ``LegacyContextEngine`` which was the always-available default.
    """

    name: str = "legacy"

    async def assemble_context(self, session_messages: list[Any] | None = None, **_: Any) -> list[Any]:
        """Return session messages unchanged."""
        return list(session_messages or [])

    async def health(self) -> dict[str, Any]:
        return {"name": self.name, "healthy": True}
