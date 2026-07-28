from __future__ import annotations

import asyncio
from typing import Any, Callable, Optional

from .event_hub import EventHub, EventHubOptions, EventStreamOptions, is_gateway_event
from .types import ConnectableOpenClawTransport, GatewayEvent, GatewayRequestOptions


RAW_EVENT_REPLAY_LIMIT = 1000


class GatewayClientTransportOptions:
    def __init__(
        self,
        url: Optional[str] = None,
        connect_challenge_timeout_ms: Optional[int] = None,
        connect_delay_ms: Optional[int] = None,
        preauth_handshake_timeout_ms: Optional[int] = None,
        tick_watch_min_interval_ms: Optional[int] = None,
        request_timeout_ms: Optional[int] = None,
        token: Optional[str] = None,
        bootstrap_token: Optional[str] = None,
        device_token: Optional[str] = None,
        password: Optional[str] = None,
        instance_id: Optional[str] = None,
        client_name: Optional[str] = None,
        client_display_name: Optional[str] = None,
        client_version: Optional[str] = None,
        platform: Optional[str] = None,
        device_family: Optional[str] = None,
        mode: Optional[str] = None,
        role: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        caps: Optional[list[str]] = None,
        commands: Optional[list[str]] = None,
        permissions: Optional[dict[str, bool]] = None,
        path_env: Optional[str] = None,
        device_identity: Optional[Any] = None,
        min_protocol: Optional[int] = None,
        max_protocol: Optional[int] = None,
        tls_fingerprint: Optional[str] = None,
        on_event: Optional[Callable[[GatewayEvent], None]] = None,
        on_hello_ok: Optional[Callable[[Any], None]] = None,
        on_connect_error: Optional[Callable[[Exception], None]] = None,
        on_reconnect_paused: Optional[Callable[[Any], None]] = None,
        on_close: Optional[Callable[[int, str], None]] = None,
        on_gap: Optional[Callable[[Any], None]] = None,
        gateway_client_class: Optional[type] = None,
    ):
        self.url = url
        self.connect_challenge_timeout_ms = connect_challenge_timeout_ms
        self.connect_delay_ms = connect_delay_ms
        self.preauth_handshake_timeout_ms = preauth_handshake_timeout_ms
        self.tick_watch_min_interval_ms = tick_watch_min_interval_ms
        self.request_timeout_ms = request_timeout_ms
        self.token = token
        self.bootstrap_token = bootstrap_token
        self.device_token = device_token
        self.password = password
        self.instance_id = instance_id
        self.client_name = client_name
        self.client_display_name = client_display_name
        self.client_version = client_version
        self.platform = platform
        self.device_family = device_family
        self.mode = mode
        self.role = role
        self.scopes = scopes
        self.caps = caps
        self.commands = commands
        self.permissions = permissions
        self.path_env = path_env
        self.device_identity = device_identity
        self.min_protocol = min_protocol
        self.max_protocol = max_protocol
        self.tls_fingerprint = tls_fingerprint
        self.on_event = on_event
        self.on_hello_ok = on_hello_ok
        self.on_connect_error = on_connect_error
        self.on_reconnect_paused = on_reconnect_paused
        self.on_close = on_close
        self.on_gap = on_gap
        self.gateway_client_class = gateway_client_class


def _to_gateway_event(event: Any) -> GatewayEvent:
    if not isinstance(event, dict):
        return {"event": "unknown"}
    event_name = event.get("event", "unknown") if isinstance(event.get("event"), str) else "unknown"
    result: GatewayEvent = {"event": event_name}
    if "payload" in event:
        result["payload"] = event["payload"]
    if isinstance(event.get("seq"), int):
        result["seq"] = event["seq"]
    if event.get("stateVersion") is not None:
        result["stateVersion"] = event["stateVersion"]
    return result


class GatewayClientTransport(ConnectableOpenClawTransport):
    def __init__(self, options: Optional[GatewayClientTransportOptions] = None):
        self._options = options or GatewayClientTransportOptions()
        self._events_hub = EventHub(EventHubOptions(replay_limit=RAW_EVENT_REPLAY_LIMIT))
        self._client: Any = None
        self._connect_promise: Optional[asyncio.Future] = None
        self._reject_pending_connect: Optional[Callable[[Exception], None]] = None
        self._close_promise: Optional[asyncio.Future] = None
        self._closed = False

    async def connect(self) -> None:
        if self._closed:
            raise Exception("gateway transport is closed")
        if self._connect_promise is not None:
            await self._connect_promise
            return

        self._connect_promise = asyncio.Future()
        self._reject_pending_connect = None

        try:
            gateway_client_class = self._options.gateway_client_class
            if gateway_client_class is None:
                from openclaw.packages.gateway_client.client import GatewayClient, GatewayClientOptions

                gateway_client_class = GatewayClient
                opts = GatewayClientOptions(
                    url=self._options.url,
                    connect_challenge_timeout_ms=self._options.connect_challenge_timeout_ms,
                    connect_delay_ms=self._options.connect_delay_ms,
                    preauth_handshake_timeout_ms=self._options.preauth_handshake_timeout_ms,
                    tick_watch_min_interval_ms=self._options.tick_watch_min_interval_ms,
                    request_timeout_ms=self._options.request_timeout_ms,
                    token=self._options.token,
                    bootstrap_token=self._options.bootstrap_token,
                    device_token=self._options.device_token,
                    password=self._options.password,
                    instance_id=self._options.instance_id,
                    client_name=self._options.client_name,
                    client_display_name=self._options.client_display_name,
                    client_version=self._options.client_version,
                    platform=self._options.platform,
                    device_family=self._options.device_family,
                    mode=self._options.mode,
                    role=self._options.role,
                    scopes=self._options.scopes,
                    caps=self._options.caps,
                    commands=self._options.commands,
                    permissions=self._options.permissions,
                    path_env=self._options.path_env,
                    device_identity=self._options.device_identity,
                    min_protocol=self._options.min_protocol,
                    max_protocol=self._options.max_protocol,
                    tls_fingerprint=self._options.tls_fingerprint,
                    on_event=self._on_event_handler,
                    on_hello_ok=self._on_hello_ok_handler,
                    on_connect_error=self._on_connect_error_handler,
                    on_reconnect_paused=self._options.on_reconnect_paused,
                    on_close=self._options.on_close,
                    on_gap=self._options.on_gap,
                )
            else:
                opts = self._options

            self._client = gateway_client_class(opts)
            self._client.start()
            await self._connect_promise
        except Exception:
            self._connect_promise = None
            raise

    def _on_event_handler(self, event: Any) -> None:
        normalized = _to_gateway_event(event)
        self._events_hub.publish(normalized)
        if self._options.on_event:
            self._options.on_event(normalized)

    def _on_hello_ok_handler(self, hello: Any) -> None:
        try:
            if self._options.on_hello_ok:
                self._options.on_hello_ok(hello)
        finally:
            if self._reject_pending_connect is not None:
                reject = self._reject_pending_connect
                self._reject_pending_connect = None
                if not self._connect_promise.done():
                    self._connect_promise.set_result(None)

    def _on_connect_error_handler(self, error: Exception) -> None:
        try:
            if self._options.on_connect_error:
                self._options.on_connect_error(error)
        finally:
            if self._client is not None and hasattr(self._client, "_stop"):
                pass
            if self._client is not None and hasattr(self._client, "stop_and_wait"):
                try:
                    asyncio.create_task(self._client.stop_and_wait())
                except Exception:
                    pass
            self._client = None
            self._connect_promise = None
            self._reject_pending_connect = None
            if self._connect_promise is not None and not self._connect_promise.done():
                self._connect_promise.set_exception(error)

    async def request(
        self,
        method: str,
        params: Any = None,
        options: Optional[GatewayRequestOptions] = None,
    ) -> Any:
        await self.connect()
        if self._client is None:
            raise Exception("gateway transport is not connected")
        return await self._client.request(method, params, options)

    def events(
        self,
        filter: Optional[Callable[[GatewayEvent], bool]] = None,
    ) -> Any:
        return self._events_hub.stream(filter, EventStreamOptions(replay=True))

    async def close(self) -> None:
        if self._close_promise is not None:
            await self._close_promise
            return
        if self._closed:
            return
        self._closed = True
        self._events_hub.close()
        client = self._client
        self._client = None
        reject_pending_connect = self._reject_pending_connect
        self._reject_pending_connect = None
        if reject_pending_connect is not None:
            reject_pending_connect(Exception("gateway transport closed before connect completed"))
        self._connect_promise = None
        if client is not None and hasattr(client, "stop_and_wait"):
            self._close_promise = asyncio.create_task(client.stop_and_wait())
        else:
            self._close_promise = asyncio.Future()
            self._close_promise.set_result(None)
        try:
            await self._close_promise
        finally:
            self._close_promise = None


def is_connectable_transport(transport: Any) -> bool:
    return hasattr(transport, "connect") and callable(getattr(transport, "connect"))
