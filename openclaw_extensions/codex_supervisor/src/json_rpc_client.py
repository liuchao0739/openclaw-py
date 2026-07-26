"""JSON-RPC transports for Codex app-server connections."""

from __future__ import annotations

import asyncio
import json
import os
import socket
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any

from websockets.asyncio.client import connect as websockets_connect

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex_supervisor.src.types import (
    CodexJsonRpcConnection,
    CodexSupervisorEndpoint,
    CodexSupervisorStdioEndpoint,
    CodexSupervisorWebSocketEndpoint,
)


def format_json_rpc_error(message: dict[str, Any]) -> RuntimeError:
    error = message.get("error")
    error_record = error if is_record(error) else {}
    detail = error_record.get("message")
    if not isinstance(detail, str):
        detail = "Codex app-server request failed"
    return RuntimeError(detail)


def format_malformed_message_error(error: Exception) -> RuntimeError:
    detail = str(error)
    return RuntimeError(f"Malformed Codex app-server message: {detail}")


def resolve_safe_approval_result(method: str) -> dict[str, Any] | None:
    if method == "item/tool/call":
        return {
            "contentItems": [
                {
                    "type": "inputText",
                    "text": (
                        "OpenClaw Codex supervisor did not register a handler for this "
                        "app-server tool call."
                    ),
                }
            ],
            "success": False,
        }
    if method == "item/commandExecution/requestApproval":
        return {"decision": "decline"}
    if method == "item/fileChange/requestApproval":
        return {"decision": "decline"}
    if method == "item/permissions/requestApproval":
        return {"permissions": {}, "scope": "turn"}
    if method.endswith("/requestApproval"):
        return {
            "decision": "decline",
            "reason": "OpenClaw Codex supervisor does not grant native approvals.",
        }
    if method == "item/tool/requestUserInput":
        return {"answers": {}}
    if method == "mcpServer/elicitation/request":
        return {"action": "decline"}
    return None


class BaseCodexJsonRpcConnection(ABC, CodexJsonRpcConnection):
    def __init__(self) -> None:
        self._pending: dict[str, tuple[asyncio.Future[Any], asyncio.TimerHandle]] = {}
        self._closed_error: Exception | None = None
        self._loop = asyncio.get_event_loop()

    @abstractmethod
    async def close(self) -> None: ...

    @abstractmethod
    def _send_raw(self, line: str) -> None: ...

    async def initialize(self) -> None:
        await self.request(
            "initialize",
            {
                "clientInfo": {
                    "name": "openclaw-codex-supervisor",
                    "title": "OpenClaw Codex Supervisor",
                    "version": "0.1.0",
                },
                "capabilities": {"experimentalApi": True},
            },
        )
        self.notify("initialized")

    async def request(self, method: str, params: dict[str, Any] | None = None) -> Any:
        if self._closed_error is not None:
            raise self._closed_error
        request_id = str(uuid.uuid4())
        payload = {"id": request_id, "method": method, "params": params or {}}
        future: asyncio.Future[Any] = self._loop.create_future()

        def on_timeout() -> None:
            self._pending.pop(request_id, None)
            if not future.done():
                future.set_exception(RuntimeError(f"Codex app-server request timed out: {method}"))

        timeout = self._loop.call_later(60.0, on_timeout)
        self._pending[request_id] = (future, timeout)
        try:
            self._send_raw(json.dumps(payload))
        except Exception:
            timeout.cancel()
            self._pending.pop(request_id, None)
            raise
        return await future

    def notify(self, method: str, params: dict[str, Any] | None = None) -> None:
        payload = {"method": method, "params": params}
        self._send_raw(json.dumps(payload))

    def _handle_message(self, message: Any) -> None:
        if not is_record(message):
            return
        message_id = message.get("id")
        request_id = message_id if isinstance(message_id, (str, int)) else None
        method = message.get("method")
        method_str = method if isinstance(method, str) else None
        if request_id is not None and method_str:
            result = resolve_safe_approval_result(method_str)
            response = (
                {
                    "id": request_id,
                    "error": {
                        "code": -32601,
                        "message": (
                            "OpenClaw Codex supervisor cannot handle app-server request: "
                            f"{method_str}"
                        ),
                    },
                }
                if result is None
                else {"id": request_id, "result": result}
            )
            self._send_raw(json.dumps(response))
            return
        if request_id is None:
            return
        pending = self._pending.pop(str(request_id), None)
        if pending is None:
            return
        future, timeout = pending
        timeout.cancel()
        if "error" in message:
            if not future.done():
                future.set_exception(format_json_rpc_error(message))
            return
        if not future.done():
            future.set_result(message.get("result"))

    def _reject_all(self, error: Exception) -> None:
        for request_id, (future, timeout) in list(self._pending.items()):
            timeout.cancel()
            self._pending.pop(request_id, None)
            if not future.done():
                future.set_exception(error)

    def _fail(self, error: Exception) -> None:
        if self._closed_error is None:
            self._closed_error = error
        self._reject_all(self._closed_error)


class StdioCodexJsonRpcConnection(BaseCodexJsonRpcConnection):
    def __init__(self, endpoint: CodexSupervisorStdioEndpoint) -> None:
        super().__init__()
        self._buffer = ""
        self._stderr_tail: list[str] = []
        self._proc = subprocess.Popen(
            [endpoint.get("command") or "codex", *(endpoint.get("args") or ["app-server", "--listen", "stdio://"])],
            cwd=endpoint.get("cwd"),
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        assert self._proc.stdout is not None
        assert self._proc.stdin is not None
        self._stdout = self._proc.stdout
        self._stdin = self._proc.stdin
        self._reader_task = asyncio.create_task(self._read_stdout())

    def _send_raw(self, line: str) -> None:
        try:
            self._stdin.write(f"{line}\n")
            self._stdin.flush()
        except Exception as error:  # noqa: BLE001
            self._fail(error)

    async def close(self) -> None:
        try:
            self._stdin.close()
        except Exception:  # noqa: BLE001, S110
            pass
        self._proc.terminate()
        self._reader_task.cancel()

    async def _read_stdout(self) -> None:
        loop = asyncio.get_event_loop()
        while True:
            chunk = await loop.run_in_executor(None, self._stdout.readline)
            if not chunk:
                self._fail(
                    RuntimeError(
                        "Codex app-server stdio transport closed. "
                        f"stderr_tail={''.join(self._stderr_tail)[:1200]}"
                    )
                )
                await self.close()
                return
            self._buffer += chunk
            while True:
                index = self._buffer.find("\n")
                if index < 0:
                    break
                line = self._buffer[:index].strip()
                self._buffer = self._buffer[index + 1 :]
                if not line:
                    continue
                try:
                    self._handle_message(json.loads(line))
                except Exception as error:  # noqa: BLE001
                    self._fail(format_malformed_message_error(error))
                    await self.close()
                    return


class WebSocketCodexJsonRpcConnection(BaseCodexJsonRpcConnection):
    def __init__(self, endpoint: CodexSupervisorWebSocketEndpoint) -> None:
        super().__init__()
        self._endpoint = endpoint
        self._ws: Any | None = None
        self._closing = False
        self._ready = asyncio.get_event_loop().create_future()
        self._connect_task = asyncio.create_task(self._connect())

    async def _connect(self) -> None:
        headers: dict[str, str] = {}
        auth_token_env = self._endpoint.get("authTokenEnv")
        if auth_token_env:
            token = os.environ.get(auth_token_env)
            if token:
                headers["authorization"] = f"Bearer {token}"
        url = self._endpoint["url"]
        try:
            if url.startswith("unix://"):
                sock = connect_codex_supervisor_unix_socket(url)
                self._ws = await websockets_connect(
                    "ws://localhost/",
                    additional_headers=headers,
                    sock=sock,
                )
            else:
                self._ws = await websockets_connect(url, additional_headers=headers)
            if not self._ready.done():
                self._ready.set_result(None)
            asyncio.create_task(self._read_messages())
        except Exception as error:  # noqa: BLE001
            if not self._ready.done():
                self._ready.set_exception(error)
            self._fail(error)

    async def ready(self) -> None:
        await self._ready

    def _send_raw(self, line: str) -> None:
        if self._ws is None:
            raise RuntimeError("Codex app-server websocket is not connected")
        asyncio.create_task(self._ws.send(line))

    async def _read_messages(self) -> None:
        if self._ws is None:
            return
        try:
            async for data in self._ws:
                text = data if isinstance(data, str) else data.decode("utf-8")
                try:
                    self._handle_message(json.loads(text))
                except Exception as error:  # noqa: BLE001
                    self._fail(format_malformed_message_error(error))
                    await self.close()
                    return
        except Exception as error:  # noqa: BLE001
            if not self._closing:
                self._fail(RuntimeError("Codex app-server websocket closed"))
                self._fail(error)

    async def close(self) -> None:
        self._closing = True
        self._fail(RuntimeError("Codex app-server websocket closed"))
        if self._ws is None:
            return
        try:
            await asyncio.wait_for(self._ws.close(), timeout=1.0)
        except Exception:  # noqa: BLE001
            await self._ws.close()


def default_codex_control_socket_path() -> str:
    codex_home = (os.environ.get("CODEX_HOME") or "").strip() or str(Path.home() / ".codex")
    return str(Path(codex_home) / "app-server-control" / "app-server-control.sock")


def resolve_unix_websocket_path(url: str) -> str:
    suffix = url[len("unix://") :]
    return suffix or default_codex_control_socket_path()


def connect_codex_supervisor_unix_socket(url: str) -> socket.socket:
    sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    sock.connect(resolve_unix_websocket_path(url))
    return sock


async def connect_codex_app_server_endpoint(
    endpoint: CodexSupervisorEndpoint,
) -> CodexJsonRpcConnection:
    connection: BaseCodexJsonRpcConnection
    if endpoint.get("transport") == "websocket":
        connection = WebSocketCodexJsonRpcConnection(endpoint)  # type: ignore[arg-type]
        await connection.ready()
    else:
        connection = StdioCodexJsonRpcConnection(endpoint)  # type: ignore[arg-type]
    try:
        await connection.initialize()
        return connection
    except Exception:
        await connection.close()
        raise
