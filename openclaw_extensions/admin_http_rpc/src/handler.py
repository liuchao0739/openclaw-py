"""HTTP handler for the Admin RPC endpoint.

It validates JSON requests, enforces the method allowlist, dispatches gateway
methods, and maps errors to HTTP.
"""

from __future__ import annotations

import json
from typing import Any, TypedDict
from uuid import uuid4

from openclaw.packages.normalization_core import is_record
from openclaw.plugin_sdk.gateway_method_runtime import dispatch_gateway_method
from openclaw_extensions.admin_http_rpc.src.methods import (
    is_admin_http_rpc_allowed_method,
    list_admin_http_rpc_allowed_methods,
)

DEFAULT_RPC_BODY_BYTES = 1024 * 1024


class RpcError(TypedDict, total=False):
    code: str
    message: str
    details: Any
    retryable: bool
    retry_after_ms: int


class ParsedRequest(TypedDict, total=False):
    id: str
    method: str
    params: Any


class _RpcResponseOk(TypedDict, total=False):
    id: str
    ok: bool
    payload: Any
    meta: dict[str, Any]


class _RpcResponseErr(TypedDict, total=False):
    id: str
    ok: bool
    error: RpcError
    meta: dict[str, Any]


RpcResponse = _RpcResponseOk | _RpcResponseErr


class ErrorCodes:
    AGENT_TIMEOUT = "AGENT_TIMEOUT"
    APPROVAL_NOT_FOUND = "APPROVAL_NOT_FOUND"
    INVALID_REQUEST = "INVALID_REQUEST"
    NOT_LINKED = "NOT_LINKED"
    NOT_PAIRED = "NOT_PAIRED"
    UNAVAILABLE = "UNAVAILABLE"


def _create_error(code: str, message: str) -> RpcError:
    return {"code": code, "message": message}


def _rpc_http_status(response: RpcResponse) -> int:
    if response.get("ok"):
        return 200
    error = response.get("error") or {}
    code = error.get("code")
    if code == ErrorCodes.INVALID_REQUEST:
        return 400
    if code == ErrorCodes.APPROVAL_NOT_FOUND:
        return 404
    if code == ErrorCodes.UNAVAILABLE:
        return 503
    if code == ErrorCodes.AGENT_TIMEOUT:
        return 504
    if code in (ErrorCodes.NOT_LINKED, ErrorCodes.NOT_PAIRED):
        return 409
    return 500


def _send_json(res: Any, status: int, body: Any) -> None:
    res.statusCode = status
    res.setHeader("Cache-Control", "no-store")
    res.setHeader("Content-Type", "application/json; charset=utf-8")
    res.end(json.dumps(body))


def _send_error(res: Any, status: int, error: dict[str, str]) -> None:
    _send_json(res, status, {"ok": False, "error": error})


async def _read_json_body(
    req: Any,
    max_bytes: int,
) -> dict[str, Any]:
    chunks: list[bytes] = []
    total_bytes = 0
    try:
        async for chunk in req:
            buffer = chunk if isinstance(chunk, bytes) else bytes(chunk)
            total_bytes += len(buffer)
            if total_bytes > max_bytes:
                return {"ok": False, "status": 413, "message": "Payload too large"}
            chunks.append(buffer)
    except Exception:  # noqa: BLE001
        return {"ok": False, "status": 400, "message": "failed to read request body"}

    raw = b"".join(chunks).decode("utf-8")
    if not raw.strip():
        return {"ok": False, "status": 400, "message": "request body must be JSON"}
    try:
        return {"ok": True, "value": json.loads(raw)}
    except json.JSONDecodeError:
        return {"ok": False, "status": 400, "message": "request body must be valid JSON"}


def _read_rpc_request_body(body: Any) -> dict[str, Any]:
    if not is_record(body):
        return {"ok": False, "message": "request body must be an object"}
    rpc_body = body
    method = rpc_body.get("method")
    if not isinstance(method, str) or not method.strip():
        return {"ok": False, "message": "method must be a non-empty string"}
    rpc_id = rpc_body.get("id")
    request_id = (
        rpc_id.strip()
        if isinstance(rpc_id, str) and rpc_id.strip()
        else str(uuid4())
    )
    request: ParsedRequest = {
        "id": request_id,
        "method": method.strip(),
    }
    if "params" in rpc_body:
        request["params"] = rpc_body["params"]
    return {"ok": True, "request": request}


def _method_not_allowed(request_id: str, method: str) -> RpcResponse:
    return {
        "id": request_id,
        "ok": False,
        "error": _create_error(
            ErrorCodes.INVALID_REQUEST,
            f"admin HTTP RPC method is not supported: {method}",
        ),
    }


def _commands_list(request_id: str) -> RpcResponse:
    return {
        "id": request_id,
        "ok": True,
        "payload": {
            "methods": list_admin_http_rpc_allowed_methods(),
        },
    }


async def _dispatch_admin_rpc(request: ParsedRequest) -> RpcResponse:
    request_id = request["id"]
    try:
        response = await dispatch_gateway_method(request["method"], request.get("params"))
        if response.get("ok"):
            result: RpcResponse = {
                "id": request_id,
                "ok": True,
                "payload": response.get("payload"),
            }
            if response.get("meta") is not None:
                result["meta"] = response["meta"]
            return result
        return {
            "id": request_id,
            "ok": False,
            "error": response.get("error")
            or _create_error(
                ErrorCodes.UNAVAILABLE,
                "gateway method failed before returning a response",
            ),
            **({"meta": response["meta"]} if response.get("meta") is not None else {}),
        }
    except Exception:  # noqa: BLE001
        return {
            "id": request_id,
            "ok": False,
            "error": _create_error(
                ErrorCodes.UNAVAILABLE,
                "gateway method failed before returning a response",
            ),
        }


async def handle_admin_http_rpc_request(req: Any, res: Any) -> bool:
    """Handle one gateway-authenticated Admin HTTP RPC request."""
    if (getattr(req, "method", None) or "GET").upper() != "POST":
        res.setHeader("Allow", "POST")
        _send_error(
            res,
            405,
            {
                "type": "method_not_allowed",
                "message": "Method Not Allowed",
            },
        )
        return True

    body = await _read_json_body(req, DEFAULT_RPC_BODY_BYTES)
    if not body.get("ok"):
        _send_error(
            res,
            int(body["status"]),
            {
                "type": "invalid_request",
                "message": str(body["message"]),
            },
        )
        return True

    parsed = _read_rpc_request_body(body["value"])
    if not parsed.get("ok"):
        _send_error(
            res,
            400,
            {
                "type": "invalid_request",
                "message": str(parsed["message"]),
            },
        )
        return True

    request = parsed["request"]
    method = request["method"]
    if not is_admin_http_rpc_allowed_method(method):
        response = _method_not_allowed(request["id"], method)
        _send_json(res, _rpc_http_status(response), response)
        return True

    if method == "commands.list":
        response = _commands_list(request["id"])
        _send_json(res, 200, response)
        return True

    response = await _dispatch_admin_rpc(request)
    _send_json(res, _rpc_http_status(response), response)
    return True
