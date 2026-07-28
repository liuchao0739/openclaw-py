from __future__ import annotations

import json
import uuid
from typing import Any

from openclaw.plugin_sdk.gateway_method_runtime import dispatch_gateway_method
from openclaw.packages.normalization_core import is_record
from openclaw_extensions.admin_http_rpc.src.methods import (
    is_admin_http_rpc_allowed_method,
    list_admin_http_rpc_allowed_methods,
)

DEFAULT_RPC_BODY_BYTES = 1024 * 1024

ERROR_CODES = {
    "AGENT_TIMEOUT": "AGENT_TIMEOUT",
    "APPROVAL_NOT_FOUND": "APPROVAL_NOT_FOUND",
    "INVALID_REQUEST": "INVALID_REQUEST",
    "NOT_LINKED": "NOT_LINKED",
    "NOT_PAIRED": "NOT_PAIRED",
    "UNAVAILABLE": "UNAVAILABLE",
}


def _create_error(code: str, message: str) -> dict[str, Any]:
    return {"code": code, "message": message}


def _rpc_http_status(response: dict[str, Any]) -> int:
    if response.get("ok"):
        return 200
    error_code = response.get("error", {}).get("code", "")
    if error_code == ERROR_CODES["INVALID_REQUEST"]:
        return 400
    if error_code == ERROR_CODES["APPROVAL_NOT_FOUND"]:
        return 404
    if error_code == ERROR_CODES["UNAVAILABLE"]:
        return 503
    if error_code == ERROR_CODES["AGENT_TIMEOUT"]:
        return 504
    if error_code in (ERROR_CODES["NOT_LINKED"], ERROR_CODES["NOT_PAIRED"]):
        return 409
    return 500


def _send_json(res: dict[str, Any], status: int, body: Any) -> None:
    res["statusCode"] = status
    res["setHeader"]("Cache-Control", "no-store")
    res["setHeader"]("Content-Type", "application/json; charset=utf-8")
    res["end"](json.dumps(body))


def _send_error(res: dict[str, Any], status: int, error: dict[str, str]) -> None:
    _send_json(res, status, {"ok": False, "error": error})


async def _read_json_body(req: dict[str, Any], max_bytes: int) -> dict[str, Any]:
    chunks: list[bytes] = []
    total_bytes = 0
    try:
        async for chunk in req:
            if isinstance(chunk, str):
                chunk = chunk.encode("utf-8")
            elif isinstance(chunk, (bytes, bytearray)):
                chunk = bytes(chunk)
            else:
                chunk = bytes(chunk)
            total_bytes += len(chunk)
            if total_bytes > max_bytes:
                return {"ok": False, "status": 413, "message": "Payload too large"}
            chunks.append(chunk)
    except Exception:
        return {"ok": False, "status": 400, "message": "failed to read request body"}
    raw = b"".join(chunks).decode("utf-8")
    if not raw.strip():
        return {"ok": False, "status": 400, "message": "request body must be JSON"}
    try:
        return {"ok": True, "value": json.loads(raw)}
    except (json.JSONDecodeError, ValueError):
        return {"ok": False, "status": 400, "message": "request body must be valid JSON"}


def _read_rpc_request_body(body: Any) -> dict[str, Any]:
    if not is_record(body):
        return {"ok": False, "message": "request body must be an object"}
    rpc_body = body
    method = rpc_body.get("method")
    if not isinstance(method, str) or not method.strip():
        return {"ok": False, "message": "method must be a non-empty string"}
    req_id = rpc_body.get("id")
    if isinstance(req_id, str) and req_id.strip():
        req_id = req_id.strip()
    else:
        req_id = str(uuid.uuid4())
    request: dict[str, Any] = {
        "id": req_id,
        "method": method.strip(),
    }
    if "params" in rpc_body:
        request["params"] = rpc_body["params"]
    return {"ok": True, "request": request}


def _method_not_allowed(req_id: str, method: str) -> dict[str, Any]:
    return {
        "id": req_id,
        "ok": False,
        "error": _create_error(
            ERROR_CODES["INVALID_REQUEST"],
            f"admin HTTP RPC method is not supported: {method}",
        ),
    }


def _commands_list(req_id: str) -> dict[str, Any]:
    return {
        "id": req_id,
        "ok": True,
        "payload": {
            "methods": list_admin_http_rpc_allowed_methods(),
        },
    }


async def _dispatch_admin_rpc(request: dict[str, Any]) -> dict[str, Any]:
    try:
        response = await dispatch_gateway_method(request["method"], request.get("params"))
        if response.get("ok"):
            result: dict[str, Any] = {
                "id": request["id"],
                "ok": True,
                "payload": response.get("payload"),
            }
            if response.get("meta"):
                result["meta"] = response["meta"]
            return result
        error_val = response.get("error")
        if error_val is None:
            error_val = _create_error(
                ERROR_CODES["UNAVAILABLE"],
                "gateway method failed before returning a response",
            )
        result = {
            "id": request["id"],
            "ok": False,
            "error": error_val,
        }
        if response.get("meta"):
            result["meta"] = response["meta"]
        return result
    except Exception:
        return {
            "id": request["id"],
            "ok": False,
            "error": _create_error(
                ERROR_CODES["UNAVAILABLE"],
                "gateway method failed before returning a response",
            ),
        }


async def handle_admin_http_rpc_request(
    req: dict[str, Any],
    res: dict[str, Any],
) -> bool:
    method = (req.get("method", "GET") or "GET").upper()
    if method != "POST":
        res["setHeader"]("Allow", "POST")
        _send_error(res, 405, {
            "type": "method_not_allowed",
            "message": "Method Not Allowed",
        })
        return True
    body = await _read_json_body(req, DEFAULT_RPC_BODY_BYTES)
    if not body.get("ok"):
        _send_error(res, body["status"], {
            "type": "invalid_request",
            "message": body["message"],
        })
        return True
    parsed = _read_rpc_request_body(body["value"])
    if not parsed.get("ok"):
        _send_error(res, 400, {
            "type": "invalid_request",
            "message": parsed["message"],
        })
        return True
    request = parsed["request"]
    if not is_admin_http_rpc_allowed_method(request["method"]):
        response = _method_not_allowed(request["id"], request["method"])
        _send_json(res, _rpc_http_status(response), response)
        return True
    if request["method"] == "commands.list":
        response = _commands_list(request["id"])
        _send_json(res, 200, response)
        return True
    response = await _dispatch_admin_rpc(request)
    _send_json(res, _rpc_http_status(response), response)
    return True