from __future__ import annotations

import asyncio
import uuid
import math
from typing import Any, Callable, Optional, Union

from .event_hub import EventHub, EventHubOptions, EventStream, is_gateway_event
from .normalize import normalize_gateway_event
from .transport import GatewayClientTransport, GatewayClientTransportOptions, is_connectable_transport
from .types import (
    AgentRunParams,
    ApprovalDecisionParams,
    ArtifactQuery,
    ArtifactsDownloadResult,
    ArtifactsGetResult,
    ArtifactsListResult,
    EnvironmentSummary,
    EnvironmentsListResult,
    GatewayEvent,
    GatewayRequestOptions,
    OpenClawEvent,
    OpenClawTransport,
    RunResult,
    RunStatus,
    RunTimestamp,
    SessionCreateParams,
    SessionSendParams,
    SessionTarget,
    TasksCancelResult,
    TasksGetResult,
    TasksListParams,
    TasksListResult,
    ToolsEffectiveParams,
    ToolInvokeParams,
    ToolInvokeResult,
)

MAX_REPLAY_RUNS = 100
MAX_REPLAY_EVENTS_PER_RUN = 500
MAX_NORMALIZED_REPLAY_EVENTS = 2000


class OpenClawOptions:
    def __init__(
        self,
        gateway: Optional[str] = None,
        url: Optional[str] = None,
        token: Optional[str] = None,
        password: Optional[str] = None,
        request_timeout_ms: Optional[int] = None,
        transport: Optional[OpenClawTransport] = None,
        gateway_client_class: Optional[type] = None,
    ):
        self.gateway = gateway
        self.url = url
        self.token = token
        self.password = password
        self.request_timeout_ms = request_timeout_ms
        self.transport = transport
        self.gateway_client_class = gateway_client_class


def _resolve_gateway_url(options: OpenClawOptions) -> Optional[str]:
    if options.url:
        return options.url
    if options.gateway and options.gateway != "auto":
        return options.gateway
    return None


def _read_optional_string(value: Any) -> Optional[str]:
    if isinstance(value, str) and len(value) > 0:
        return value
    return None


def _read_optional_timestamp(value: Any) -> Optional[RunTimestamp]:
    if isinstance(value, str) and len(value) > 0:
        return value
    if isinstance(value, (int, float)) and value == value:
        return int(value)
    return None


def _normalize_timeout_ms(timeout_ms: Optional[int]) -> Optional[int]:
    if timeout_ms is None:
        return None
    if not isinstance(timeout_ms, (int, float)) or timeout_ms != timeout_ms or timeout_ms < 0:
        raise Exception("timeoutMs must be a finite non-negative number")
    return int(math.floor(timeout_ms))


def _timeout_seconds_from_ms(timeout_ms: Optional[int]) -> Optional[int]:
    normalized = _normalize_timeout_ms(timeout_ms)
    if normalized is None:
        return None
    if normalized == 0:
        return 0
    return int(math.ceil(normalized / 1000))


def _split_model_ref(model: Optional[str]) -> dict[str, str]:
    if not model:
        return {}
    index = model.find("/")
    if index <= 0 or index == len(model) - 1:
        return {"model": model}
    return {
        "provider": model[:index],
        "model": model[index + 1:],
    }


def _run_status_from_wait_payload(payload: Any) -> RunStatus:
    record = payload if isinstance(payload, dict) else {}
    status = record.get("status")
    status_lower = status.lower() if isinstance(status, str) else None
    stop_reason = record.get("stopReason")
    stop_reason_lower = stop_reason.lower() if isinstance(stop_reason, str) else ""
    pending_error = record.get("pendingError") is True
    timeout_phase = record.get("timeoutPhase")
    timeout_phase_lower = timeout_phase.lower() if isinstance(timeout_phase, str) else None
    status_already_timeout_attributed = status_lower in ("timeout", "timed_out")

    hard_timeout = (
        not pending_error
        and (
            (stop_reason_lower != "restart"
             and record.get("providerStarted") is True
             and status_already_timeout_attributed)
            or timeout_phase_lower in ("preflight", "provider", "post_turn")
        )
    )

    has_terminal_timeout_metadata = (
        _read_optional_timestamp(record.get("endedAt")) is not None
        or (not pending_error and _read_optional_string(record.get("error")) is not None)
        or len(stop_reason_lower) > 0
        or isinstance(record.get("livenessState"), str)
        or record.get("yielded") is True
    )

    if hard_timeout:
        return "timed_out"

    if status_lower in ("aborted", "cancelled", "canceled", "killed") or stop_reason_lower in (
        "aborted", "cancelled", "canceled", "killed", "auth-revoked", "restart", "rpc", "user"
    ) or (record.get("aborted") is True and stop_reason_lower == "stop"):
        return "cancelled"

    if status_lower in ("ok", "completed", "succeeded"):
        return "completed"

    if status_lower == "timeout":
        if stop_reason_lower in ("timeout", "timed_out") or record.get("aborted") is True or has_terminal_timeout_metadata:
            return "timed_out"
        return "accepted"

    if status_lower == "timed_out":
        return "timed_out"

    if status_lower == "accepted":
        return "accepted"

    return "failed"


def _assert_no_unsupported_run_options(params: AgentRunParams) -> None:
    unsupported = []
    if params.get("workspace"):
        unsupported.append("workspace")
    if params.get("runtime"):
        unsupported.append("runtime")
    if params.get("environment"):
        unsupported.append("environment")
    if params.get("approvals"):
        unsupported.append("approvals")
    if not unsupported:
        return
    raise Exception(
        f"OpenClaw Gateway does not support per-run SDK option{'s' if len(unsupported) != 1 else ''} yet: {', '.join(unsupported)}"
    )


def _build_agent_params(params: AgentRunParams) -> dict[str, Any]:
    _assert_no_unsupported_run_options(params)
    model_ref = _split_model_ref(params.get("model"))
    timeout_seconds = _timeout_seconds_from_ms(params.get("timeoutMs"))
    result: dict[str, Any] = {
        "message": params.get("input", ""),
        "idempotencyKey": params.get("idempotencyKey") or str(uuid.uuid4()),
    }
    if params.get("agentId"):
        result["agentId"] = params["agentId"]
    if model_ref.get("provider"):
        result["provider"] = model_ref["provider"]
    if model_ref.get("model"):
        result["model"] = model_ref["model"]
    if params.get("sessionId"):
        result["sessionId"] = params["sessionId"]
    if params.get("sessionKey"):
        result["sessionKey"] = params["sessionKey"]
    if params.get("thinking"):
        result["thinking"] = params["thinking"]
    if isinstance(params.get("deliver"), bool):
        result["deliver"] = params["deliver"]
    if params.get("attachments"):
        result["attachments"] = params["attachments"]
    if timeout_seconds is not None:
        result["timeout"] = timeout_seconds
    if params.get("label"):
        result["label"] = params["label"]
    return result


def _unsupported_gateway_api(api: str) -> Any:
    raise Exception(f"{api} is not supported by the current OpenClaw Gateway yet")


def _as_record(value: Any) -> dict[str, Any]:
    if isinstance(value, dict):
        return value
    return {}


def _has_artifact_query_scope(params: Any) -> bool:
    record = _as_record(params)
    return any(
        isinstance(v, str) and len(v.strip()) > 0
        for v in [record.get("sessionKey"), record.get("runId"), record.get("taskId")]
    )


def _require_artifact_query_scope(api: str, params: Any) -> ArtifactQuery:
    if not _has_artifact_query_scope(params):
        raise Exception(f"{api} requires one of sessionKey, runId, or taskId")
    return params


def _has_tools_effective_session_key(params: Any) -> bool:
    record = _as_record(params)
    return isinstance(record.get("sessionKey"), str) and len(record["sessionKey"].strip()) > 0


def _require_tools_effective_session_key(params: Any) -> ToolsEffectiveParams:
    if not _has_tools_effective_session_key(params):
        raise Exception("oc.tools.effective requires sessionKey")
    return params


ChatProjectionState = str
ChatProjection = dict[str, Any]


def _read_chat_projection(event: OpenClawEvent) -> Optional[ChatProjection]:
    raw = event.get("raw")
    if event.get("type") != "raw" or not raw or raw.get("event") != "chat":
        return None
    payload = _as_record(raw.get("payload"))
    state = payload.get("state")
    if state in ("delta", "final"):
        return {"state": state, "payload": payload}
    return None


def _read_chat_projection_text(payload: dict[str, Any]) -> Optional[str]:
    message = _as_record(payload.get("message"))
    content = message.get("content")
    if isinstance(content, str):
        return content
    if not isinstance(content, list):
        return None
    text_parts = []
    for part in content:
        record = _as_record(part)
        if record.get("type") == "text" and isinstance(record.get("text"), str):
            text_parts.append(record["text"])
    text = "".join(text_parts)
    return text if len(text) > 0 else None


def _read_chat_projection_delta_text(payload: dict[str, Any]) -> Optional[str]:
    delta = payload.get("deltaText")
    if isinstance(delta, str):
        return delta
    return None


def _read_chat_projection_replace(payload: dict[str, Any]) -> bool:
    return payload.get("replace") is True


def _is_assistant_run_event(event: OpenClawEvent) -> bool:
    return event.get("type") in ("assistant.delta", "assistant.message")


def _is_terminal_run_event(event: OpenClawEvent) -> bool:
    return event.get("type") in ("run.completed", "run.failed", "run.cancelled", "run.timed_out")


def _normalize_chat_projection_event(
    event: OpenClawEvent,
    projection: ChatProjection,
    previous_text: Optional[str],
) -> OpenClawEvent:
    text = _read_chat_projection_text(projection["payload"])
    delta_text = _read_chat_projection_delta_text(projection["payload"])
    has_previous_text = previous_text is not None
    is_replacement = _read_chat_projection_replace(projection["payload"])
    state = projection["state"]

    result: OpenClawEvent = {**event}
    if state == "delta":
        if text is not None:
            data: dict[str, Any] = {
                "text": text,
                "delta": (delta_text if delta_text is not None else text) if has_previous_text else text,
            }
            if is_replacement:
                data["replace"] = True
            result["data"] = data
        else:
            result["data"] = event.get("data")
    else:
        data = {"phase": "end"}
        if text is not None:
            data["outputText"] = text
        result["data"] = data
        if state == "final":
            result["type"] = "run.completed"

    return result


class Agent:
    def __init__(self, client: "OpenClaw", id: str):
        self._client = client
        self.id = id

    async def run(self, input: Union[str, dict]) -> "Run":
        if isinstance(input, str):
            params: AgentRunParams = {"input": input, "agentId": self.id}
        else:
            params = {**input, "agentId": self.id}
        return await self._client.runs.create(params)

    async def identity(self, params: Optional[dict] = None) -> Any:
        request_params: dict[str, Any] = {"agentId": self.id}
        if params and params.get("sessionKey"):
            request_params["sessionKey"] = params["sessionKey"]
        return await self._client.request("agent.identity.get", request_params)


class Run:
    def __init__(self, client: "OpenClaw", id: str, session_key: Optional[str] = None):
        self._client = client
        self.id = id
        self._session_key = session_key

    def events(
        self,
        filter: Optional[Callable[[OpenClawEvent], bool]] = None,
    ) -> Any:
        return self._client.run_events(self.id, filter)

    async def wait(self, options: Optional[dict] = None) -> RunResult:
        timeout_ms = _normalize_timeout_ms(options.get("timeoutMs") if options else None)
        params: dict[str, Any] = {"runId": self.id}
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        raw = await self._client.request("agent.wait", params, {"timeoutMs": None})
        record = _as_record(raw)
        status = _run_status_from_wait_payload(raw)
        error_str = _read_optional_string(record.get("error"))
        error_result = None
        if error_str:
            error_result = {"message": error_str}
        result: RunResult = {
            "runId": self.id,
            "status": status,
            "sessionKey": _read_optional_string(record.get("sessionKey")) or self._session_key,
            "raw": raw,
        }
        session_id = _read_optional_string(record.get("sessionId"))
        if session_id:
            result["sessionId"] = session_id
        started_at = _read_optional_timestamp(record.get("startedAt"))
        if started_at is not None:
            result["startedAt"] = started_at
        ended_at = _read_optional_timestamp(record.get("endedAt"))
        if ended_at is not None:
            result["endedAt"] = ended_at
        if error_result:
            result["error"] = error_result
        return result

    async def cancel(self) -> Any:
        params: dict[str, Any] = {"runId": self.id}
        if self._session_key:
            params["key"] = self._session_key
        return await self._client.request("sessions.abort", params)


class Session:
    def __init__(self, client: "OpenClaw", key: str, info: Any = None):
        self._client = client
        self.key = key
        self._info = info

    async def send(self, input: Union[str, dict]) -> "Run":
        if isinstance(input, str):
            params: SessionSendParams = {"key": self.key, "message": input}
        else:
            params = {**input, "key": self.key}
        timeout_ms = _normalize_timeout_ms(params.get("timeoutMs"))
        if timeout_ms is not None:
            params["timeoutMs"] = timeout_ms
        request_options: GatewayRequestOptions = {"expectFinal": True}
        if timeout_ms is not None:
            request_options["timeoutMs"] = None if timeout_ms == 0 else timeout_ms
        raw = await self._client.request("sessions.send", params, request_options)
        record = _as_record(raw)
        run_id = _read_optional_string(record.get("runId"))
        if not run_id:
            raise Exception("sessions.send did not return a runId")
        return Run(self._client, run_id, self.key)

    async def abort(self, run_id: Optional[str] = None) -> Any:
        params: dict[str, Any] = {"key": self.key}
        if run_id:
            params["runId"] = run_id
        return await self._client.request("sessions.abort", params)

    async def patch(self, params: dict[str, Any]) -> Any:
        return await self._client.request("sessions.patch", {**params, "key": self.key})

    async def compact(self, params: Optional[dict] = None) -> Any:
        request_params: dict[str, Any] = {"key": self.key}
        if params:
            request_params.update(params)
        return await self._client.request("sessions.compact", request_params)


class AgentsNamespace:
    def __init__(self, client: "OpenClaw"):
        self._client = client

    async def list(self, params: Any = None) -> Any:
        return await self._client.request("agents.list", params if params is not None else {})

    async def get(self, id: str) -> Agent:
        return Agent(self._client, id)

    async def create(self, params: dict) -> Any:
        return await self._client.request("agents.create", params)

    async def update(self, params: dict) -> Any:
        return await self._client.request("agents.update", params)

    async def delete(self, params: dict) -> Any:
        return await self._client.request("agents.delete", params)


class SessionsNamespace:
    def __init__(self, client: "OpenClaw"):
        self._client = client

    async def list(self, params: Any = None) -> Any:
        return await self._client.request("sessions.list", params if params is not None else {})

    async def create(self, params: Optional[SessionCreateParams] = None) -> Session:
        raw = await self._client.request("sessions.create", params or {})
        record = _as_record(raw)
        key = _read_optional_string(record.get("key")) or _read_optional_string(record.get("sessionKey"))
        if not key:
            if params and params.get("key"):
                key = params["key"]
        if not key:
            raise Exception("sessions.create did not return a session key")
        return Session(self._client, key, raw)

    async def get(self, target: Union[SessionTarget, str]) -> Session:
        key = target if isinstance(target, str) else target.get("key", "")
        return Session(self._client, key)

    async def resolve(self, params: dict) -> Any:
        return await self._client.request("sessions.resolve", params)

    async def send(self, input: SessionSendParams) -> Run:
        return await Session(self._client, input.get("key", "")).send(input)


class RunsNamespace:
    def __init__(self, client: "OpenClaw"):
        self._client = client

    async def create(self, params: AgentRunParams) -> Run:
        timeout_ms = _normalize_timeout_ms(params.get("timeoutMs"))
        normalized_params = {**params, "timeoutMs": timeout_ms} if timeout_ms is not None else params
        request_options: GatewayRequestOptions = {"expectFinal": False}
        if timeout_ms is not None:
            request_options["timeoutMs"] = None if timeout_ms == 0 else timeout_ms
        raw = await self._client.request("agent", _build_agent_params(normalized_params), request_options)
        record = _as_record(raw)
        run_id = _read_optional_string(record.get("runId"))
        if not run_id:
            raise Exception("agent did not return a runId")
        return Run(
            self._client,
            run_id,
            _read_optional_string(record.get("sessionKey")) or params.get("sessionKey"),
        )

    async def get(self, run_id: str) -> Run:
        return Run(self._client, run_id)

    def events(self, run_id: str) -> Any:
        return Run(self._client, run_id).events()

    async def wait(self, run_id: str, options: Optional[dict] = None) -> RunResult:
        return await Run(self._client, run_id).wait(options)

    async def cancel(self, run_id: str, session_key: Optional[str] = None) -> Any:
        return await Run(self._client, run_id, session_key).cancel()


class RpcNamespace:
    def __init__(self, client: "OpenClaw", prefix: str):
        self._client = client
        self._prefix = prefix

    async def call(self, method: str, params: Any = None, options: Optional[GatewayRequestOptions] = None) -> Any:
        return await self._client.request(f"{self._prefix}.{method}", params, options)


class TasksNamespace(RpcNamespace):
    def __init__(self, client: "OpenClaw"):
        super().__init__(client, "tasks")

    async def list(self, params: Optional[TasksListParams] = None) -> TasksListResult:
        return await self.call("list", params if params is not None else {})

    async def get(self, task_id: str) -> TasksGetResult:
        return await self.call("get", {"taskId": task_id})

    async def cancel(self, task_id: str, options: Optional[dict] = None) -> TasksCancelResult:
        request_params: dict[str, Any] = {"taskId": task_id}
        if options and options.get("reason"):
            request_params["reason"] = options["reason"]
        return await self.call("cancel", request_params)


class ModelsNamespace(RpcNamespace):
    def __init__(self, client: "OpenClaw"):
        super().__init__(client, "models")

    async def list(self, params: Any = None) -> Any:
        return await self.call("list", params if params is not None else {})

    async def status(self, params: Any = None) -> Any:
        return await self.call("authStatus", params)


class ToolsNamespace(RpcNamespace):
    def __init__(self, client: "OpenClaw"):
        super().__init__(client, "tools")

    async def list(self, params: Any = None) -> Any:
        return await self.call("catalog", params if params is not None else {})

    async def effective(self, params: ToolsEffectiveParams) -> Any:
        return await self.call("effective", _require_tools_effective_session_key(params))

    async def invoke(self, name: str, params: Optional[ToolInvokeParams] = None) -> ToolInvokeResult:
        request_params: dict[str, Any] = {"name": name}
        if params:
            if params.get("args"):
                request_params["args"] = params["args"]
            if params.get("sessionKey"):
                request_params["sessionKey"] = params["sessionKey"]
            if params.get("agentId"):
                request_params["agentId"] = params["agentId"]
            if isinstance(params.get("confirm"), bool):
                request_params["confirm"] = params["confirm"]
            if params.get("idempotencyKey"):
                request_params["idempotencyKey"] = params["idempotencyKey"]
        return await self.call("invoke", request_params)


class ArtifactsNamespace(RpcNamespace):
    def __init__(self, client: "OpenClaw"):
        super().__init__(client, "artifacts")

    async def list(self, params: ArtifactQuery) -> ArtifactsListResult:
        return await self.call("list", _require_artifact_query_scope("oc.artifacts.list", params))

    async def get(self, id: str, params: ArtifactQuery) -> ArtifactsGetResult:
        request_params = {**_require_artifact_query_scope("oc.artifacts.get", params), "artifactId": id}
        return await self.call("get", request_params)

    async def download(self, id: str, params: ArtifactQuery) -> ArtifactsDownloadResult:
        request_params = {**_require_artifact_query_scope("oc.artifacts.download", params), "artifactId": id}
        return await self.call("download", request_params)


class ApprovalsNamespace:
    def __init__(self, client: "OpenClaw"):
        self._client = client

    async def list(self, params: Any = None) -> Any:
        return await self._client.request("exec.approval.list", params if params is not None else {})

    async def respond(self, approval_id: str, params: ApprovalDecisionParams) -> Any:
        return await self._client.request("exec.approval.resolve", {
            "id": approval_id,
            "decision": params.get("decision"),
        })


class EnvironmentsNamespace(RpcNamespace):
    def __init__(self, client: "OpenClaw"):
        super().__init__(client, "environments")

    async def list(self, params: Any = None) -> EnvironmentsListResult:
        return await self.call("list", params if params is not None else {})

    async def create(self, params: Any = None) -> Any:
        _ = params
        return _unsupported_gateway_api("oc.environments.create")

    async def status(self, environment_id: str) -> EnvironmentSummary:
        return await self.call("status", {"environmentId": environment_id})

    async def delete(self, environment_id: str) -> Any:
        _ = environment_id
        return _unsupported_gateway_api("oc.environments.delete")


class OpenClaw:
    def __init__(self, options: Optional[OpenClawOptions] = None):
        opts = options or OpenClawOptions()
        if opts.transport is not None:
            self._transport: OpenClawTransport = opts.transport
        else:
            self._transport = GatewayClientTransport(
                GatewayClientTransportOptions(
                    url=_resolve_gateway_url(opts),
                    token=opts.token,
                    password=opts.password,
                    request_timeout_ms=opts.request_timeout_ms,
                    gateway_client_class=opts.gateway_client_class,
                )
            )
        self.agents = AgentsNamespace(self)
        self.sessions = SessionsNamespace(self)
        self.runs = RunsNamespace(self)
        self.tasks = TasksNamespace(self)
        self.models = ModelsNamespace(self)
        self.tools = ToolsNamespace(self)
        self.artifacts = ArtifactsNamespace(self)
        self.approvals = ApprovalsNamespace(self)
        self.environments = EnvironmentsNamespace(self)

        self._normalized_events = EventHub(EventHubOptions(replay_limit=MAX_NORMALIZED_REPLAY_EVENTS))
        self._replay_by_run_id: dict[str, list[OpenClawEvent]] = {}
        self._connected = False
        self._closed = False
        self._event_pump_promise: Optional[asyncio.Future] = None
        self._event_pump_ready: Optional[asyncio.Future] = None
        self._close_promise: Optional[asyncio.Future] = None

    async def connect(self) -> None:
        self._assert_open()
        if self._connected:
            await self._start_event_pump()
            self._assert_open()
            return
        if is_connectable_transport(self._transport):
            await self._transport.connect()
        self._assert_open()
        self._connected = True
        await self._start_event_pump()
        self._assert_open()

    async def close(self) -> None:
        if self._close_promise is not None:
            await self._close_promise
            return
        if self._closed:
            return
        self._closed = True

        async def _do_close():
            try:
                if hasattr(self._transport, "close"):
                    close_result = self._transport.close()
                    if asyncio.iscoroutine(close_result):
                        await close_result
                if self._event_pump_promise is not None:
                    try:
                        await self._event_pump_promise
                    except Exception:
                        pass
            finally:
                self._normalized_events.close()
                self._event_pump_promise = None
                self._event_pump_ready = None
                self._connected = False

        self._close_promise = asyncio.create_task(_do_close())
        try:
            await self._close_promise
        finally:
            self._close_promise = None

    async def request(
        self,
        method: str,
        params: Any = None,
        options: Optional[GatewayRequestOptions] = None,
    ) -> Any:
        await self.connect()
        self._assert_open()
        return await self._transport.request(method, params, options)

    def events(
        self,
        filter: Optional[Callable[[OpenClawEvent], bool]] = None,
    ) -> Any:
        return self._iterate_events(filter)

    def run_events(
        self,
        run_id: str,
        filter: Optional[Callable[[OpenClawEvent], bool]] = None,
    ) -> Any:
        return self._iterate_run_events(run_id, filter)

    def raw_events(
        self,
        filter: Optional[Callable[[GatewayEvent], bool]] = None,
    ) -> Any:
        self._assert_open()
        return self._transport.events(filter)

    def _assert_open(self) -> None:
        if self._closed:
            raise Exception("OpenClaw SDK client is closed")

    async def _iterate_events(
        self,
        filter: Optional[Callable[[OpenClawEvent], bool]],
    ):
        await self.connect()
        self._assert_open()
        stream = self._normalized_events.stream(filter)
        async for event in stream:
            yield event

    async def _iterate_run_events(
        self,
        run_id: str,
        filter: Optional[Callable[[OpenClawEvent], bool]],
    ):
        await self.connect()
        self._assert_open()
        replay_events = self._replay_snapshot(run_id)
        has_canonical_assistant_run_event = any(_is_assistant_run_event(e) for e in replay_events)
        has_terminal_run_event = any(_is_terminal_run_event(e) for e in replay_events)
        previous_chat_projection_text: Optional[str] = None

        def to_run_stream_event(event: OpenClawEvent) -> Optional[OpenClawEvent]:
            nonlocal has_canonical_assistant_run_event, has_terminal_run_event, previous_chat_projection_text
            chat_projection = _read_chat_projection(event)
            if chat_projection and chat_projection["state"] == "delta":
                if has_canonical_assistant_run_event:
                    return None
                run_event = _normalize_chat_projection_event(event, chat_projection, previous_chat_projection_text)
                text = _read_chat_projection_text(chat_projection["payload"])
                if text is not None:
                    previous_chat_projection_text = text
                return run_event
            if chat_projection and chat_projection["state"] == "final":
                if has_terminal_run_event:
                    return None
                has_terminal_run_event = True
                return _normalize_chat_projection_event(event, chat_projection, previous_chat_projection_text)
            if _is_assistant_run_event(event):
                has_canonical_assistant_run_event = True
            if _is_terminal_run_event(event):
                has_terminal_run_event = True
            return event

        def matches(event: OpenClawEvent) -> bool:
            return event.get("runId") == run_id

        live_source = self._normalized_events.stream(matches)
        seen: set[str] = set()

        try:
            for event in replay_events:
                if event["id"] in seen:
                    continue
                seen.add(event["id"])
                run_event = to_run_stream_event(event)
                if run_event is None:
                    continue
                if filter and not filter(run_event):
                    continue
                yield run_event

            async for next_event in live_source:
                if next_event["id"] in seen:
                    continue
                seen.add(next_event["id"])
                run_event = to_run_stream_event(next_event)
                if run_event is None:
                    continue
                if filter and not filter(run_event):
                    continue
                yield run_event
        finally:
            if hasattr(live_source, "aclose"):
                try:
                    await live_source.aclose()
                except Exception:
                    pass

    async def _start_event_pump(self) -> None:
        if self._event_pump_ready is not None:
            await self._event_pump_ready
            return

        ready_future: asyncio.Future = asyncio.Future()

        async def _mark_ready():
            if ready_future.done():
                return
            ready_future.set_result(None)

        self._event_pump_ready = ready_future

        async def _pump():
            try:
                stream = self._transport.events()
                async for raw_event in stream:
                    if not ready_future.done():
                        await _mark_ready()
                    normalized = normalize_gateway_event(raw_event)
                    self._record_replay_event(normalized)
                    self._normalized_events.publish(normalized)
            except Exception as error:
                await _mark_ready()
                self._normalized_events.close(error)
                return
            await _mark_ready()
            self._normalized_events.close()

        self._event_pump_promise = asyncio.create_task(_pump())
        await ready_future

    def _record_replay_event(self, event: OpenClawEvent) -> None:
        run_id = event.get("runId")
        if not run_id:
            return
        if run_id not in self._replay_by_run_id:
            if len(self._replay_by_run_id) >= MAX_REPLAY_RUNS:
                oldest_run_id = next(iter(self._replay_by_run_id))
                del self._replay_by_run_id[oldest_run_id]
            self._replay_by_run_id[run_id] = []
        events = self._replay_by_run_id[run_id]
        events.append(event)
        if len(events) > MAX_REPLAY_EVENTS_PER_RUN:
            overflow = len(events) - MAX_REPLAY_EVENTS_PER_RUN
            del events[:overflow]

    def _replay_snapshot(self, run_id: str) -> list[OpenClawEvent]:
        return list(self._replay_by_run_id.get(run_id, []))
