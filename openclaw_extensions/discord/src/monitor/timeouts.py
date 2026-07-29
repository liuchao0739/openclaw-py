import asyncio
from typing import Any, Optional


DISCORD_ATTACHMENT_IDLE_TIMEOUT_MS = 60_000
DISCORD_ATTACHMENT_TOTAL_TIMEOUT_MS = 5 * 60_000
DISCORD_DEFAULT_INBOUND_WORKER_TIMEOUT_MS = 30_000
DISCORD_DEFAULT_LISTENER_TIMEOUT_MS = 60_000


def merge_abort_signals(*signals: Any) -> Optional[Any]:
    valid_signals = [s for s in signals if s is not None]
    if not valid_signals:
        return None
    if len(valid_signals) == 1:
        return valid_signals[0]
    return {"merged": True, "signals": valid_signals}


async def with_abort_timeout(params: dict):
    timeout_ms = params.get("timeoutMs")
    run = params["run"]

    if timeout_ms is None:
        return await run(None)

    async def run_with_timeout():
        try:
            return await asyncio.wait_for(run(None), timeout=timeout_ms / 1000)
        except asyncio.TimeoutError:
            create_timeout_error = params.get("createTimeoutError")
            raise create_timeout_error() if create_timeout_error else TimeoutError(
                f"timed out after {timeout_ms}ms"
            )

    return await run_with_timeout()
