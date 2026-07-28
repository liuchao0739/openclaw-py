from __future__ import annotations

import asyncio
from typing import Callable, Optional

from .event_loop_ready import (
    EventLoopReadyOptions,
    EventLoopReadyResult,
    wait_for_event_loop_ready,
)
from .timeouts import resolve_connect_challenge_timeout_ms


class GatewayClientStartable:
    def start(self) -> None:
        ...


EventLoopReadyWaiter = Callable[
    [Optional[EventLoopReadyOptions]],
    asyncio.Future[EventLoopReadyResult],
]


class GatewayClientStartReadinessOptions:
    def __init__(
        self,
        *,
        timeout_ms: Optional[int] = None,
        client_options: Optional[dict] = None,
        abort_event: Optional[asyncio.Event] = None,
    ):
        self.timeout_ms = timeout_ms
        self.client_options = client_options or {}
        self.abort_event = abort_event


def _resolve_gateway_client_start_readiness_timeout_ms(
    options: Optional[GatewayClientStartReadinessOptions] = None,
) -> int:
    if options is None:
        options = GatewayClientStartReadinessOptions()

    if options.timeout_ms is not None and options.timeout_ms == int(options.timeout_ms):
        return int(options.timeout_ms)

    client_opts = options.client_options or {}
    timeout_override = None
    challenge_timeout = client_opts.get("connectChallengeTimeoutMs")
    if challenge_timeout is not None and challenge_timeout == int(challenge_timeout):
        timeout_override = int(challenge_timeout)
    else:
        delay_ms = client_opts.get("connectDelayMs")
        if delay_ms is not None and delay_ms == int(delay_ms):
            timeout_override = int(delay_ms)

    env = client_opts.get("env")
    configured_timeout_ms = client_opts.get("preauthHandshakeTimeoutMs")

    return resolve_connect_challenge_timeout_ms(
        timeout_override,
        params={
            "env": env,
            "configuredTimeoutMs": configured_timeout_ms,
        },
    )


async def start_gateway_client_with_readiness_wait(
    wait_for_ready: EventLoopReadyWaiter,
    client: GatewayClientStartable,
    options: Optional[GatewayClientStartReadinessOptions] = None,
) -> EventLoopReadyResult:
    if options is None:
        options = GatewayClientStartReadinessOptions()

    readiness = await wait_for_ready(
        EventLoopReadyOptions(
            max_wait_ms=_resolve_gateway_client_start_readiness_timeout_ms(options),
            abort_event=options.abort_event,
        ),
    )
    if readiness.ready and not readiness.aborted:
        if options.abort_event is None or not options.abort_event.is_set():
            client.start()
    return readiness


async def start_gateway_client_when_event_loop_ready(
    client: GatewayClientStartable,
    options: Optional[GatewayClientStartReadinessOptions] = None,
) -> EventLoopReadyResult:
    return await start_gateway_client_with_readiness_wait(
        wait_for_event_loop_ready,
        client,
        options,
    )
