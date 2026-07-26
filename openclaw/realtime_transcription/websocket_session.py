"""Realtime transcription websocket session streams audio to transcription providers.

Mirrors src/realtime-transcription/websocket-session.ts.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import Callable
from typing import Any, TypeVar

from websockets.asyncio.client import connect as websockets_connect

EventT = TypeVar("EventT")

DEFAULT_CONNECT_TIMEOUT_MS = 10_000
DEFAULT_CLOSE_TIMEOUT_MS = 5_000
DEFAULT_MAX_RECONNECT_ATTEMPTS = 5
DEFAULT_RECONNECT_DELAY_MS = 1000
DEFAULT_MAX_QUEUED_BYTES = 2 * 1024 * 1024


def _default_parse_message(payload: bytes) -> Any:
    try:
        return json.loads(payload.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as error:
        raise RuntimeError("Realtime transcription websocket received malformed JSON.") from error


class _RealtimeTranscriptionWebSocketTransport:
    def __init__(self, session: WebSocketRealtimeTranscriptionSession[Any]) -> None:
        self._session = session
        self.callbacks = session.options["callbacks"]

    def close_now(self) -> None:
        self._session._closed = True
        self._session._force_close()

    def fail_connect(self, error: Exception) -> None:
        if self._session._fail_connect is not None:
            self._session._fail_connect(error)

    def is_open(self) -> bool:
        ws = self._session._ws
        return ws is not None and not ws.close_code

    def is_ready(self) -> bool:
        return self._session._ready

    def mark_ready(self) -> None:
        if self._session._mark_ready is not None:
            self._session._mark_ready()

    def send_binary(self, payload: bytes) -> bool:
        return self._session._send_binary(payload)

    def send_json(self, payload: Any) -> bool:
        return self._session._send_json(payload)


class WebSocketRealtimeTranscriptionSession:
    def __init__(self, options: dict[str, Any]) -> None:
        self.options = options
        self._flow_id = str(uuid.uuid4())
        self._close_timer: asyncio.TimerHandle | None = None
        self._closed = False
        self._connected = False
        self._current_url = ""
        self._queued_audio: list[bytes] = []
        self._queued_bytes = 0
        self._ready = False
        self._reconnect_attempts = 0
        self._reconnecting = False
        self._suppress_reconnect = False
        self._ws: Any | None = None
        self._transport = _RealtimeTranscriptionWebSocketTransport(self)
        self._fail_connect: Callable[[Exception], None] | None = None
        self._mark_ready: Callable[[], None] | None = None
        self._reader_task: asyncio.Task[None] | None = None
        self._connect_lock = asyncio.Lock()

    @property
    def _close_timeout_ms(self) -> int:
        return int(self.options.get("closeTimeoutMs") or DEFAULT_CLOSE_TIMEOUT_MS)

    @property
    def _connect_timeout_ms(self) -> int:
        return int(self.options.get("connectTimeoutMs") or DEFAULT_CONNECT_TIMEOUT_MS)

    @property
    def _max_queued_bytes(self) -> int:
        return int(self.options.get("maxQueuedBytes") or DEFAULT_MAX_QUEUED_BYTES)

    @property
    def _max_reconnect_attempts(self) -> int:
        return int(self.options.get("maxReconnectAttempts") or DEFAULT_MAX_RECONNECT_ATTEMPTS)

    @property
    def _reconnect_delay_ms(self) -> int:
        return int(self.options.get("reconnectDelayMs") or DEFAULT_RECONNECT_DELAY_MS)

    async def connect(self) -> None:
        self._closed = False
        self._suppress_reconnect = False
        self._reconnect_attempts = 0
        await self._do_connect()

    def send_audio(self, audio: bytes) -> None:
        if self._closed or not audio:
            return
        if self._ws is not None and not self._ws.close_code and self._ready:
            send_audio = self.options["sendAudio"]
            send_audio(audio, self._transport)
            return
        self._queue_audio(audio)

    def close(self) -> None:
        self._closed = True
        self._connected = False
        self._ready = False
        self._queued_audio = []
        self._queued_bytes = 0
        if self._ws is None or self._ws.close_code:
            self._force_close()
            return
        on_close = self.options.get("onClose")
        if on_close is not None:
            try:
                on_close(self._transport)
            except Exception as error:  # noqa: BLE001
                self._emit_error(error)
        loop = asyncio.get_event_loop()
        self._close_timer = loop.call_later(
            self._close_timeout_ms / 1000,
            self._force_close,
        )

    def is_connected(self) -> bool:
        return self._connected and self._ready

    async def _do_connect(self) -> None:
        async with self._connect_lock:
            loop = asyncio.get_event_loop()
            settled = False
            opened = False
            connect_timeout: asyncio.TimerHandle | None = None
            connect_future: asyncio.Future[None] = loop.create_future()

            def normalize_error(error: Any) -> Exception:
                return error if isinstance(error, Exception) else RuntimeError(str(error))

            def clear_connect_timeout() -> None:
                nonlocal connect_timeout
                if connect_timeout is not None:
                    connect_timeout.cancel()
                    connect_timeout = None

            def finish_closed_connect() -> None:
                nonlocal settled
                if settled:
                    return
                settled = True
                clear_connect_timeout()
                if not connect_future.done():
                    connect_future.set_result(None)

            def finish_connect() -> None:
                nonlocal settled
                if settled:
                    return
                settled = True
                clear_connect_timeout()
                self._ready = True
                self._flush_queued_audio()
                if not connect_future.done():
                    connect_future.set_result(None)

            def fail_connect(error: Exception) -> None:
                nonlocal settled
                if settled:
                    return
                settled = True
                clear_connect_timeout()
                self._emit_error(error)
                self._suppress_reconnect = True
                self._force_close()
                if not connect_future.done():
                    connect_future.set_exception(error)

            self._mark_ready = finish_connect
            self._fail_connect = fail_connect

            def on_connect_timeout() -> None:
                fail_connect(
                    RuntimeError(
                        self.options.get("connectTimeoutMessage")
                        or f"{self.options['providerId']} realtime transcription connection timeout"
                    )
                )

            connect_timeout = loop.call_later(self._connect_timeout_ms / 1000, on_connect_timeout)

            try:
                connection = await self._resolve_connection()
            except Exception as error:  # noqa: BLE001
                fail_connect(normalize_error(error))
                await connect_future
                return

            if settled:
                await connect_future
                return
            if self._closed:
                finish_closed_connect()
                await connect_future
                return

            self._current_url = connection["url"]
            headers = connection.get("headers")

            try:
                self._ws = await websockets_connect(
                    self._current_url,
                    additional_headers=headers,
                    open_timeout=self._connect_timeout_ms / 1000,
                )
            except Exception as error:  # noqa: BLE001
                fail_connect(normalize_error(error))
                await connect_future
                return

            opened = True
            self._connected = True
            self._reconnect_attempts = 0

            try:
                on_open = self.options.get("onOpen")
                if on_open is not None:
                    on_open(self._transport)
                if self.options.get("readyOnOpen"):
                    finish_connect()
            except Exception as error:  # noqa: BLE001
                fail_connect(normalize_error(error))
                await connect_future
                return

            self._reader_task = asyncio.create_task(
                self._read_messages(
                    opened=opened,
                    settled=lambda: settled,
                    fail_connect=fail_connect,
                    clear_connect_timeout=clear_connect_timeout,
                )
            )

            await connect_future

    async def _read_messages(
        self,
        *,
        opened: bool,
        settled: Callable[[], bool],
        fail_connect: Callable[[Exception], None],
        clear_connect_timeout: Callable[[], None],
    ) -> None:
        ws = self._ws
        if ws is None:
            return
        should_reconnect = False
        try:
            async for data in ws:
                payload = data if isinstance(data, bytes) else data.encode("utf-8")
                try:
                    on_message = self.options.get("onMessage")
                    if on_message is None:
                        continue
                    parse_message = self.options.get("parseMessage") or _default_parse_message
                    on_message(parse_message(payload), self._transport)
                except Exception as error:  # noqa: BLE001
                    self._emit_error(error)
        except Exception as error:  # noqa: BLE001
            normalized = error if isinstance(error, Exception) else RuntimeError(str(error))
            if not opened or not settled():
                fail_connect(normalized)
                return
            self._emit_error(normalized)
        finally:
            clear_connect_timeout()
            self._connected = False
            self._ready = False
            if self._close_timer is not None:
                self._close_timer.cancel()
                self._close_timer = None
            if not self._closed and not self._suppress_reconnect and opened and settled():
                should_reconnect = True
            if self._suppress_reconnect:
                self._suppress_reconnect = False

        if self._closed:
            return
        if not opened or not settled():
            fail_connect(
                RuntimeError(
                    self.options.get("connectClosedBeforeReadyMessage")
                    or (
                        f"{self.options['providerId']} realtime transcription connection "
                        "closed before ready"
                    )
                )
            )
            return
        if should_reconnect:
            await self._attempt_reconnect()

    async def _resolve_connection(self) -> dict[str, Any]:
        url_option = self.options["url"]
        url = await url_option() if callable(url_option) else url_option
        headers_option = self.options.get("headers")
        headers = await headers_option() if callable(headers_option) else headers_option
        return {"url": url, "headers": headers}

    async def _attempt_reconnect(self) -> None:
        if self._closed or self._reconnecting:
            return
        if self._reconnect_attempts >= self._max_reconnect_attempts:
            self._emit_error(
                RuntimeError(
                    self.options.get("reconnectLimitMessage")
                    or (
                        f"{self.options['providerId']} realtime transcription reconnect "
                        "limit reached"
                    )
                )
            )
            return
        self._reconnect_attempts += 1
        delay = self._reconnect_delay_ms * (2 ** (self._reconnect_attempts - 1))
        self._reconnecting = True
        try:
            await asyncio.sleep(delay / 1000)
            if not self._closed:
                await self._do_connect()
        except Exception:  # noqa: BLE001
            if not self._closed:
                self._reconnecting = False
                await self._attempt_reconnect()
        finally:
            self._reconnecting = False

    def _queue_audio(self, audio: bytes) -> None:
        self._queued_audio.append(bytes(audio))
        self._queued_bytes += len(audio)
        while self._queued_bytes > self._max_queued_bytes and self._queued_audio:
            dropped = self._queued_audio.pop(0)
            self._queued_bytes -= len(dropped)

    def _flush_queued_audio(self) -> None:
        send_audio = self.options["sendAudio"]
        for audio in self._queued_audio:
            send_audio(audio, self._transport)
        self._queued_audio = []
        self._queued_bytes = 0

    def _send_binary(self, payload: bytes) -> bool:
        ws = self._ws
        if ws is None or ws.close_code:
            return False
        asyncio.create_task(ws.send(payload))
        return True

    def _send_json(self, payload: Any) -> bool:
        ws = self._ws
        if ws is None or ws.close_code:
            return False
        asyncio.create_task(ws.send(json.dumps(payload)))
        return True

    def _force_close(self) -> None:
        if self._close_timer is not None:
            self._close_timer.cancel()
            self._close_timer = None
        self._connected = False
        self._ready = False
        if self._reader_task is not None:
            self._reader_task.cancel()
            self._reader_task = None
        if self._ws is not None:
            asyncio.create_task(self._ws.close(1000, "Transcription session closed"))
            self._ws = None

    def _emit_error(self, error: Any) -> None:
        normalized = error if isinstance(error, Exception) else RuntimeError(str(error))
        callbacks = self.options["callbacks"]
        on_error = callbacks.get("onError")
        if on_error is None:
            return
        try:
            on_error(normalized)
        except Exception:  # noqa: BLE001
            return


def create_realtime_transcription_websocket_session(
    options: dict[str, Any],
) -> WebSocketRealtimeTranscriptionSession:
    """Create a reusable websocket session wrapper for a provider implementation."""
    return WebSocketRealtimeTranscriptionSession(options)
