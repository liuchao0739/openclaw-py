"""Shared gateway RPC command options and progress-wrapped CLI call helper."""

from __future__ import annotations

from typing import Any, TypedDict

DEFAULT_GATEWAY_RPC_TIMEOUT_MS = 10_000


class GatewayRpcOpts(TypedDict, total=False):
    config: dict[str, Any]
    url: str
    token: str
    password: str
    timeout: str
    expectFinal: bool
    json: bool


def parse_timeout_ms_with_fallback(
    timeout: str | None,
    fallback: int = DEFAULT_GATEWAY_RPC_TIMEOUT_MS,
) -> int:
    """Parse a timeout string with fallback."""
    if not timeout:
        return fallback
    try:
        value = int(timeout)
        return value if value > 0 else fallback
    except (ValueError, TypeError):
        return fallback


async def call_gateway_cli(
    method: str,
    opts: dict[str, Any],
    params: Any | None = None,
) -> dict[str, Any]:
    """Call a gateway RPC method with progress wrapping.

    Deferred to the gateway client; returns an error dict when unavailable.
    """
    timeout_ms = parse_timeout_ms_with_fallback(
        opts.get("timeout"),
        DEFAULT_GATEWAY_RPC_TIMEOUT_MS,
    )

    try:
        from openclaw.gateway.call import call_gateway

        return await call_gateway(
            config=opts.get("config"),
            url=opts.get("url"),
            token=opts.get("token"),
            password=opts.get("password"),
            method=method,
            params=params,
            expectFinal=bool(opts.get("expectFinal")),
            timeoutMs=timeout_ms,
            clientName="cli",
            mode="cli",
        )
    except Exception as err:
        return {"ok": False, "error": str(err)}
