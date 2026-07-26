"""Channel config helper utilities.

Mirrors openclaw/plugin-sdk/channel-config-helpers.ts (subset).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import TypeVar

TResult = TypeVar("TResult")
TConfig = TypeVar("TConfig")


def adapt_scoped_account_accessor(
    accessor: Callable[[dict[str, TConfig | str | None]], TResult],
) -> Callable[[dict[str, TConfig], str | None], TResult]:
    """Adapt ``{cfg, accountId}`` accessors to callback sites that pass positional args."""

    def adapted(cfg: dict[str, TConfig], account_id: str | None = None) -> TResult:
        return accessor({"cfg": cfg, "accountId": account_id})

    return adapted
