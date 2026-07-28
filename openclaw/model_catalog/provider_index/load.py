from __future__ import annotations

from typing import Any

from .normalize import normalize_openclaw_provider_index
from .openclaw_provider_index import OPENCLAW_PROVIDER_INDEX
from .types import OpenClawProviderIndex


def load_openclaw_provider_index(
    source: Any = OPENCLAW_PROVIDER_INDEX,
) -> OpenClawProviderIndex:
    result = normalize_openclaw_provider_index(source)
    if result is None:
        return {"version": 1, "providers": {}}
    return result


__all__ = [
    "load_openclaw_provider_index",
]
