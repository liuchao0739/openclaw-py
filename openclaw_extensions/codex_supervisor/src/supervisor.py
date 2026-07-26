"""Codex app-server supervisor for session listing, reads, and turn controls."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from typing import Any

from openclaw.packages.normalization_core import is_record
from openclaw_extensions.codex_supervisor.src.json_rpc_client import (
    connect_codex_app_server_endpoint,
)
from openclaw_extensions.codex_supervisor.src.types import (
    CodexJsonRpcConnection,
    CodexSupervisorEndpoint,
    CodexSupervisorEndpointHealth,
    CodexSupervisorSendResult,
    CodexSupervisorSession,
    CodexSupervisorSessionListResult,
    CodexSupervisorThreadStatus,
    CodexSupervisorTurnMode,
)

EndpointConnector = Callable[[CodexSupervisorEndpoint], Awaitable[CodexJsonRpcConnection]]

ALL_CODEX_THREAD_SOURCE_KINDS = ["cli", "vscode", "exec", "appServer", "unknown"]
DEFAULT_MAX_STORED_SESSIONS = 200


def as_record_array(value: Any) -> list[dict[str, Any]]:
    if not isinstance(value, list):
        return []
    return [entry for entry in value if is_record(entry)]


def extract_thread(value: Any) -> dict[str, Any] | None:
    if not is_record(value):
        return None
    thread = value.get("thread")
    return thread if is_record(thread) else None


def extract_thread_list(value: Any) -> list[dict[str, Any]]:
    if not is_record(value):
        return []
    for key in ("data", "threads", "loadedThreads"):
        listed = value.get(key)
        if isinstance(listed, list):
            return as_record_array(listed)
    return []


def extract_string_list(value: Any) -> list[str]:
    if not is_record(value) or not isinstance(value.get("data"), list):
        return []
    return [entry for entry in value["data"] if isinstance(entry, str)]


def get_status_type(thread: dict[str, Any]) -> CodexSupervisorThreadStatus:
    status = thread.get("status")
    if is_record(status) and isinstance(status.get("type"), str):
        return status["type"]
    if isinstance(status, str):
        return status
    return "unknown"


def to_session(
    endpoint_id: str,
    thread: dict[str, Any],
    human_attached: bool | None = None,
) -> CodexSupervisorSession | None:
    if not isinstance(thread.get("id"), str):
        return None
    session: CodexSupervisorSession = {
        "endpointId": endpoint_id,
        "threadId": thread["id"],
        "status": get_status_type(thread),
    }
    if isinstance(thread.get("sessionId"), str):
        session["sessionId"] = thread["sessionId"]
    if isinstance(thread.get("cwd"), str):
        session["cwd"] = thread["cwd"]
    if isinstance(thread.get("preview"), str):
        session["preview"] = thread["preview"]
    if "name" in thread and (isinstance(thread["name"], str) or thread["name"] is None):
        session["name"] = thread["name"]
    if isinstance(thread.get("source"), str):
        session["source"] = thread["source"]
    if isinstance(thread.get("updatedAt"), int):
        session["updatedAt"] = thread["updatedAt"]
    if human_attached is not None:
        session["humanAttached"] = human_attached
    return session


def find_in_progress_turn_id(thread: dict[str, Any]) -> str | None:
    turns = as_record_array(thread.get("turns"))
    for turn in reversed(turns):
        if turn.get("status") == "inProgress" and isinstance(turn.get("id"), str):
            return turn["id"]
    return None


def is_loaded_thread_read_miss(error: Exception) -> bool:
    message = str(error)
    return "thread not found" in message or "thread not loaded" in message


class CodexSupervisor:
    def __init__(
        self,
        endpoints: list[CodexSupervisorEndpoint],
        connector: EndpointConnector = connect_codex_app_server_endpoint,
    ) -> None:
        self._endpoints = endpoints
        self._connector = connector
        self._connections: dict[str, asyncio.Future[CodexJsonRpcConnection]] = {}

    def list_endpoints(self) -> list[CodexSupervisorEndpoint]:
        return self._endpoints

    async def close(self) -> None:
        settled = await asyncio.gather(*self._connections.values(), return_exceptions=True)
        self._connections.clear()
        for entry in settled:
            if isinstance(entry, Exception):
                continue
            await entry.close()

    async def probe_endpoints(self) -> list[CodexSupervisorEndpointHealth]:
        results: list[CodexSupervisorEndpointHealth] = []
        for endpoint in self._endpoints:
            try:
                connection = await self._connection_for(endpoint["id"])
                await connection.request("thread/loaded/list", {"limit": 1})
                results.append({"endpointId": endpoint["id"], "ok": True})
            except Exception as error:  # noqa: BLE001
                self._forget_endpoint(endpoint["id"])
                results.append(
                    {
                        "endpointId": endpoint["id"],
                        "ok": False,
                        "detail": str(error),
                    }
                )
        return results

    async def list_sessions(
        self,
        params: dict[str, Any] | None = None,
    ) -> list[CodexSupervisorSession]:
        snapshot = await self.list_session_snapshot(params or {})
        return snapshot["sessions"]

    async def list_session_snapshot(
        self,
        params: dict[str, Any] | None = None,
    ) -> CodexSupervisorSessionListResult:
        options = params or {}
        sessions: list[CodexSupervisorSession] = []
        errors: list[CodexSupervisorEndpointHealth] = []
        for endpoint in self._endpoints:
            try:
                sessions.extend(await self._list_endpoint_sessions(endpoint, options))
            except Exception as error:  # noqa: BLE001
                self._forget_endpoint(endpoint["id"])
                errors.append(
                    {
                        "endpointId": endpoint["id"],
                        "ok": False,
                        "detail": str(error),
                    }
                )
        return {"sessions": sessions, "errors": errors}

    async def read_session(self, params: dict[str, Any]) -> dict[str, Any]:
        endpoint_id = await self._resolve_endpoint_id(params)
        connection = await self._connection_for(endpoint_id)
        try:
            result = await self._read_thread(
                connection,
                str(params["threadId"]),
                params.get("includeTurns") is True,
            )
            if not is_record(result):
                raise RuntimeError("Codex thread/read returned a non-object response")
            return result
        except Exception:
            self._forget_endpoint(endpoint_id)
            raise

    async def send_to_session(self, params: dict[str, Any]) -> CodexSupervisorSendResult:
        endpoint_id = await self._resolve_endpoint_id(params)
        connection = await self._connection_for(endpoint_id)
        try:
            mode: CodexSupervisorTurnMode = params.get("mode") or "auto"
            thread_id = str(params["threadId"])
            text = str(params["text"])
            if mode == "start":
                return await self._start_turn(connection, endpoint_id, thread_id, text)
            read = await self._read_thread(connection, thread_id, False)
            thread = extract_thread(read)
            if thread is None:
                raise RuntimeError(f"Codex thread not found: {thread_id}")
            status = get_status_type(thread)
            if mode == "steer" or status == "active":
                detailed = await self._read_thread(connection, thread_id, True)
                detailed_thread = extract_thread(detailed)
                turn_id = (
                    find_in_progress_turn_id(detailed_thread)
                    if detailed_thread
                    else None
                ) or find_in_progress_turn_id(thread) or await self._read_active_turn_id(
                    connection, thread_id
                )
                if turn_id is None:
                    raise RuntimeError(
                        f"Codex thread {thread_id} is active but no in-progress turn is readable"
                    )
                await connection.request(
                    "turn/steer",
                    {
                        "threadId": thread_id,
                        "expectedTurnId": turn_id,
                        "input": [{"type": "text", "text": text, "text_elements": []}],
                    },
                )
                return {
                    "endpointId": endpoint_id,
                    "threadId": thread_id,
                    "mode": "steer",
                    "turnId": turn_id,
                    "status": status,
                }
            return await self._start_turn(connection, endpoint_id, thread_id, text)
        except Exception:
            self._forget_endpoint(endpoint_id)
            raise

    async def interrupt_session(self, params: dict[str, Any]) -> dict[str, str]:
        endpoint_id = await self._resolve_endpoint_id(params)
        connection = await self._connection_for(endpoint_id)
        thread_id = str(params["threadId"])
        try:
            turn_id = params.get("turnId")
            if not isinstance(turn_id, str):
                read = await self._read_thread(connection, thread_id, True)
                thread = extract_thread(read)
                turn_id = (
                    find_in_progress_turn_id(thread) if thread else None
                ) or await self._read_active_turn_id(connection, thread_id)
            if not isinstance(turn_id, str):
                raise RuntimeError(  # noqa: TRY004
                    f"Codex thread {thread_id} has no readable in-progress turn"
                )
            await connection.request("turn/interrupt", {"threadId": thread_id, "turnId": turn_id})
            return {"endpointId": endpoint_id, "threadId": thread_id, "turnId": turn_id}
        except Exception:
            self._forget_endpoint(endpoint_id)
            raise

    async def _list_endpoint_sessions(
        self,
        endpoint: CodexSupervisorEndpoint,
        params: dict[str, Any],
    ) -> list[CodexSupervisorSession]:
        if params.get("includeStored") is True:
            loaded = await self._list_loaded_thread_sessions(endpoint)
            sessions = list(loaded)
            for stored in await self._list_stored_thread_sessions(
                endpoint,
                params.get("maxStoredSessions"),
            ):
                if not any(session["threadId"] == stored["threadId"] for session in sessions):
                    sessions.append(stored)
            return sessions
        return await self._list_loaded_thread_sessions(endpoint)

    async def _list_loaded_thread_sessions(
        self,
        endpoint: CodexSupervisorEndpoint,
    ) -> list[CodexSupervisorSession]:
        sessions: list[CodexSupervisorSession] = []
        connection = await self._connection_for(endpoint["id"])
        cursor: str | None = None
        while True:
            listed = await connection.request(
                "thread/loaded/list",
                {"limit": 100, **({"cursor": cursor} if cursor else {})},
            )
            for thread_id in extract_string_list(listed):
                if any(entry["threadId"] == thread_id for entry in sessions):
                    continue
                read = await self._read_optional_loaded_thread(connection, thread_id)
                thread = extract_thread(read)
                session = to_session(endpoint["id"], thread, True) if thread else None
                if session is not None:
                    sessions.append(session)
            cursor = listed.get("nextCursor") if is_record(listed) else None
            cursor = cursor if isinstance(cursor, str) else None
            if not cursor:
                break
        return sessions

    async def _list_stored_thread_sessions(
        self,
        endpoint: CodexSupervisorEndpoint,
        max_stored_sessions: Any = DEFAULT_MAX_STORED_SESSIONS,
    ) -> list[CodexSupervisorSession]:
        session_limit = (
            min(1000, max(1, int(max_stored_sessions)))
            if isinstance(max_stored_sessions, (int, float))
            and max_stored_sessions == int(max_stored_sessions)
            else DEFAULT_MAX_STORED_SESSIONS
        )
        sessions: list[CodexSupervisorSession] = []
        connection = await self._connection_for(endpoint["id"])
        cursor: str | None = None
        while True:
            remaining = session_limit - len(sessions)
            if remaining <= 0:
                break
            listed = await connection.request(
                "thread/list",
                {
                    "limit": min(100, remaining),
                    "sourceKinds": ALL_CODEX_THREAD_SOURCE_KINDS,
                    "useStateDbOnly": True,
                    **({"cursor": cursor} if cursor else {}),
                },
            )
            for thread in extract_thread_list(listed):
                thread_id = thread.get("id")
                if not isinstance(thread_id, str):
                    continue
                if any(
                    entry["endpointId"] == endpoint["id"] and entry["threadId"] == thread_id
                    for entry in sessions
                ):
                    continue
                session = to_session(endpoint["id"], thread)
                if session is not None:
                    sessions.append(session)
                    if len(sessions) >= session_limit:
                        break
            cursor = listed.get("nextCursor") if is_record(listed) else None
            cursor = cursor if isinstance(cursor, str) else None
            if not cursor:
                break
        return sessions

    async def _read_optional_loaded_thread(
        self,
        connection: CodexJsonRpcConnection,
        thread_id: str,
    ) -> Any:
        try:
            return await self._read_loaded_thread(connection, thread_id, False)
        except Exception as error:
            if is_loaded_thread_read_miss(error):
                return None
            raise

    async def _read_loaded_thread(
        self,
        connection: CodexJsonRpcConnection,
        thread_id: str,
        include_turns: bool,
    ) -> Any:
        try:
            return await connection.request(
                "thread/read",
                {"threadId": thread_id, "includeTurns": include_turns},
            )
        except Exception as error:
            if not include_turns:
                raise
            message = str(error)
            if "not materialized yet" not in message:
                raise
            return await connection.request(
                "thread/read",
                {"threadId": thread_id, "includeTurns": False},
            )

    async def _start_turn(
        self,
        connection: CodexJsonRpcConnection,
        endpoint_id: str,
        thread_id: str,
        text: str,
    ) -> CodexSupervisorSendResult:
        result = await connection.request(
            "turn/start",
            {
                "threadId": thread_id,
                "input": [{"type": "text", "text": text, "text_elements": []}],
            },
        )
        turn = result.get("turn") if is_record(result) else None
        turn_record = turn if is_record(turn) else None
        payload: CodexSupervisorSendResult = {
            "endpointId": endpoint_id,
            "threadId": thread_id,
            "mode": "start",
        }
        if turn_record and isinstance(turn_record.get("id"), str):
            payload["turnId"] = turn_record["id"]
        if turn_record and isinstance(turn_record.get("status"), str):
            payload["status"] = turn_record["status"]
        return payload

    async def _read_thread(
        self,
        connection: CodexJsonRpcConnection,
        thread_id: str,
        include_turns: bool,
    ) -> Any:
        return await self._read_loaded_thread(connection, thread_id, include_turns)

    async def _read_active_turn_id(
        self,
        connection: CodexJsonRpcConnection,
        thread_id: str,
    ) -> str | None:
        try:
            response = await connection.request(
                "thread/turns/list",
                {
                    "threadId": thread_id,
                    "limit": 10,
                    "sortDirection": "desc",
                    "itemsView": "summary",
                },
            )
            for turn in extract_thread_list(response):
                if turn.get("status") == "inProgress" and isinstance(turn.get("id"), str):
                    return turn["id"]
        except Exception:  # noqa: BLE001
            return None
        return None

    async def _resolve_endpoint_id(self, params: dict[str, Any]) -> str:
        endpoint_id = params.get("endpointId")
        if isinstance(endpoint_id, str):
            return endpoint_id
        thread_id = str(params["threadId"])
        sessions = await self.list_sessions()
        matches = [session for session in sessions if session["threadId"] == thread_id]
        if len(matches) == 1:
            return matches[0]["endpointId"]
        if len(matches) > 1:
            raise RuntimeError(f"Codex thread id is ambiguous across endpoints: {thread_id}")
        endpoint_ids: set[str] = set()
        for endpoint in self._endpoints:
            if endpoint["id"] in endpoint_ids:
                continue
            try:
                connection = await self._connection_for(endpoint["id"])
                read = await self._read_thread(connection, thread_id, False)
                thread = extract_thread(read)
                if thread and thread.get("id") == thread_id:
                    endpoint_ids.add(endpoint["id"])
            except Exception as error:  # noqa: BLE001
                if is_loaded_thread_read_miss(error):
                    continue
                self._forget_endpoint(endpoint["id"])
        if len(endpoint_ids) == 1:
            return next(iter(endpoint_ids))
        if len(endpoint_ids) > 1:
            raise RuntimeError(f"Codex thread id is ambiguous across endpoints: {thread_id}")
        raise RuntimeError(f"Codex thread not found: {thread_id}")

    async def _connection_for(self, endpoint_id: str) -> CodexJsonRpcConnection:
        endpoint = next((entry for entry in self._endpoints if entry["id"] == endpoint_id), None)
        if endpoint is None:
            raise RuntimeError(f"Unknown Codex supervisor endpoint: {endpoint_id}")
        existing = self._connections.get(endpoint_id)
        if existing is not None:
            return await existing
        created = asyncio.ensure_future(self._connector(endpoint))
        self._connections[endpoint_id] = created

        def _cleanup(future: asyncio.Future[CodexJsonRpcConnection]) -> None:
            if self._connections.get(endpoint_id) is future:
                self._connections.pop(endpoint_id, None)

        created.add_done_callback(_cleanup)
        return await created

    def _forget_endpoint(self, endpoint_id: str) -> None:
        existing = self._connections.pop(endpoint_id, None)
        if existing is None:
            return

        async def _close_connection() -> None:
            try:
                connection = await existing
                await connection.close()
            except Exception:  # noqa: BLE001
                return

        asyncio.create_task(_close_connection())
