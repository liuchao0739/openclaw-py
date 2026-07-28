from __future__ import annotations

from typing import Any


def resolve_oauth_identity(
    credential: dict[str, Any],
) -> dict[str, Any]:
    return {
        "provider": credential.get("provider"),
        "email": credential.get("email"),
        "name": credential.get("name"),
        "avatar": credential.get("avatar"),
    }
