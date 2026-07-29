import asyncio
import json
import uuid
from pathlib import Path
from typing import Any, Optional

from .a2ui_jsonl import build_a2ui_text_jsonl, validate_a2ui_jsonl
from .cli_helpers import canvas_snapshot_temp_path, parse_canvas_snapshot_payload


def _normalize_optional_string(value: Any) -> Optional[str]:
    if value is None:
        return None
    if isinstance(value, str):
        return value
    return str(value)


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip().lower()
    return str(value).strip().lower()


def _parse_strict_positive_integer(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        parsed = int(str(value))
    except (ValueError, TypeError):
        return None
    return parsed if parsed > 0 else None


def _parse_strict_finite_number(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(str(value))
    except (ValueError, TypeError):
        return None
    return parsed


def _parse_canvas_snapshot_request_format(raw: Any) -> str:
    format_val = _normalize_lowercase_string_or_empty(_normalize_optional_string(raw) or "jpg")
    if format_val == "png":
        return "png"
    if format_val in ("jpg", "jpeg"):
        return "jpeg"
    raise ValueError(f"invalid format: {raw} (expected png|jpg|jpeg)")


def _parse_timeout_ms(raw: Any) -> Optional[int]:
    if raw is None:
        return None
    parsed = _parse_strict_positive_integer(raw)
    if parsed is None:
        raise ValueError("--invoke-timeout must be a positive integer.")
    return parsed


def _parse_canvas_positive_int_option(raw: Optional[str], flag: str) -> Optional[int]:
    if not raw:
        return None
    parsed = _parse_strict_positive_integer(raw)
    if parsed is None:
        raise ValueError(f"{flag} must be a positive integer.")
    return parsed


def _parse_canvas_finite_number_option(raw: Optional[str], flag: str) -> Optional[float]:
    if not raw:
        return None
    parsed = _parse_strict_finite_number(raw)
    if parsed is None:
        raise ValueError(f"{flag} must be a number.")
    return parsed


def _parse_canvas_snapshot_quality_option(raw: Optional[str]) -> Optional[float]:
    parsed = _parse_canvas_finite_number_option(raw, "--quality")
    if parsed is not None and (parsed < 0 or parsed > 1):
        raise ValueError("--quality must be between 0 and 1.")
    return parsed


def _parse_node_candidates(raw: Any) -> list:
    if not isinstance(raw, dict):
        return []
    node_list = raw.get("nodes")
    if not isinstance(node_list, list):
        node_list = raw.get("paired")
        if not isinstance(node_list, list):
            node_list = []
    candidates = []
    for entry in node_list:
        if not isinstance(entry, dict):
            continue
        node_id = entry.get("nodeId")
        if not isinstance(node_id, str):
            continue
        candidate = {"nodeId": node_id}
        if isinstance(entry.get("displayName"), str):
            candidate["displayName"] = entry["displayName"]
        if isinstance(entry.get("remoteIp"), str):
            candidate["remoteIp"] = entry["remoteIp"]
        if isinstance(entry.get("connected"), bool):
            candidate["connected"] = entry["connected"]
        if isinstance(entry.get("clientId"), str):
            candidate["clientId"] = entry["clientId"]
        candidates.append(candidate)
    return candidates


def _resolve_node_from_node_list(candidates: list, query: str) -> dict:
    if not candidates:
        raise ValueError("no nodes available")
    if not query:
        return candidates[0]
    for candidate in candidates:
        if (
            candidate.get("nodeId") == query
            or candidate.get("displayName") == query
            or candidate.get("remoteIp") == query
        ):
            return candidate
    return candidates[0]


def _unauthorized_hint_for_message(message: str) -> Optional[str]:
    haystack = _normalize_lowercase_string_or_empty(message)
    if (
        "unauthorizedclient" in haystack
        or "bridge client is not authorized" in haystack
        or "unsigned bridge clients are not allowed" in haystack
    ):
        return (
            "peekaboo bridge rejected the client. "
            "sign the peekaboo CLI (TeamID Y5PE65HELJ) or launch the host with "
            "PEEKABOO_ALLOW_UNSIGNED_SOCKET_CLIENTS=1 for local dev."
        )
    return None


def _shorten_home_path(file_path: str) -> str:
    home = str(Path.home())
    if file_path.startswith(home):
        return "~" + file_path[len(home):]
    return file_path


def create_default_canvas_cli_dependencies() -> dict:
    def nodes_call_opts(cmd_parser, defaults=None):
        timeout_ms = (defaults or {}).get("timeoutMs", 10_000)
        cmd_parser.add_argument("--url", help="Gateway WebSocket URL")
        cmd_parser.add_argument("--token", help="Gateway token")
        cmd_parser.add_argument("--timeout", default=str(timeout_ms), help="Timeout in ms")
        cmd_parser.add_argument("--json", action="store_true", help="Output JSON")
        return cmd_parser

    async def call_gateway_cli(method, opts, params=None, call_opts=None):
        return {}

    def run_nodes_command(label, action):
        try:
            asyncio.get_event_loop().run_until_complete(action())
        except Exception as err:
            message = str(err)
            default_runtime = {"log": print, "error": print, "exit": lambda c: None, "writeJson": lambda v: print(json.dumps(v))}
            default_runtime["error"](f"nodes {label} failed: {message}")
            hint = _unauthorized_hint_for_message(message)
            if hint:
                default_runtime["error"](hint)
            default_runtime["exit"](1)

    async def resolve_node_id(opts, query):
        try:
            raw = await call_gateway_cli("node.list", opts, {})
        except Exception:
            raw = await call_gateway_cli("node.pair.list", opts, {})
        return _resolve_node_from_node_list(_parse_node_candidates(raw), query)["nodeId"]

    def build_node_invoke_params(node_id, command, params=None, timeout_ms=None):
        result = {
            "nodeId": node_id,
            "command": command,
            "params": params,
            "idempotencyKey": str(uuid.uuid4()),
        }
        if isinstance(timeout_ms, (int, float)):
            result["timeoutMs"] = timeout_ms
        return result

    async def write_base64_to_file(file_path, base64_data):
        import base64
        with open(file_path, "wb") as f:
            f.write(base64.b64decode(base64_data))

    return {
        "defaultRuntime": {
            "log": print,
            "error": print,
            "exit": lambda c: None,
            "writeJson": lambda v: print(json.dumps(v)),
        },
        "nodesCallOpts": nodes_call_opts,
        "runNodesCommand": run_nodes_command,
        "getNodesTheme": lambda: {"ok": lambda v: v},
        "parseTimeoutMs": _parse_timeout_ms,
        "resolveNodeId": resolve_node_id,
        "buildNodeInvokeParams": build_node_invoke_params,
        "callGatewayCli": call_gateway_cli,
        "writeBase64ToFile": write_base64_to_file,
        "shortenHomePath": _shorten_home_path,
    }


async def _invoke_canvas(deps: dict, opts: dict, command: str, params: dict = None):
    timeout_ms = deps["parseTimeoutMs"](opts.get("invokeTimeout"))
    node_id = await deps["resolveNodeId"](opts, _normalize_optional_string(opts.get("node")) or "")
    return await deps["callGatewayCli"](
        "node.invoke",
        opts,
        deps["buildNodeInvokeParams"](
            node_id=node_id,
            command=command,
            params=params,
            timeout_ms=timeout_ms if isinstance(timeout_ms, (int, float)) else None,
        ),
    )


def register_nodes_canvas_commands(nodes_parser, deps: dict):
    import argparse

    canvas_parser = nodes_parser.add_subparsers(dest="canvas", help="Capture or render canvas content from a paired node")

    def add_nodes_call_opts(parser, defaults=None):
        return deps["nodesCallOpts"](parser, defaults)

    def add_common_node_opts(parser):
        parser.add_argument("--node", required=True, help="Node id, name, or IP")
        parser.add_argument("--invoke-timeout", default=None, help="Node invoke timeout in ms")

    snapshot_parser = canvas_parser.add_parser("snapshot", help="Capture a canvas snapshot")
    snapshot_parser.add_argument("--format", default="jpg", help="Image format")
    snapshot_parser.add_argument("--max-width", default=None, help="Max width in px")
    snapshot_parser.add_argument("--quality", default=None, help="JPEG quality")
    add_common_node_opts(snapshot_parser)
    snapshot_parser.add_argument("--timeout", default="60000")
    snapshot_parser.add_argument("--json", action="store_true")

    async def snapshot_action(opts):
        fmt = _parse_canvas_snapshot_request_format(opts.get("format"))
        max_width = _parse_canvas_positive_int_option(opts.get("max_width"), "--max-width")
        quality = _parse_canvas_snapshot_quality_option(opts.get("quality"))
        raw = await _invoke_canvas(deps, opts, "canvas.snapshot", {
            "format": fmt,
            "maxWidth": max_width if max_width is not None else None,
            "quality": quality if quality is not None else None,
        })
        res = raw if isinstance(raw, dict) else {}
        payload = parse_canvas_snapshot_payload(res.get("payload"))
        file_path = canvas_snapshot_temp_path(
            ext="jpg" if payload["format"] == "jpeg" else payload["format"]
        )
        await deps["writeBase64ToFile"](file_path, payload["base64"])
        if opts.get("json"):
            deps["defaultRuntime"]["writeJson"]({"file": {"path": file_path, "format": payload["format"]}})
            return
        deps["defaultRuntime"]["log"](deps["shortenHomePath"](file_path))

    snapshot_parser.set_defaults(func=snapshot_action)

    present_parser = canvas_parser.add_parser("present", help="Show the canvas")
    present_parser.add_argument("--target", default=None, help="Target URL/path")
    present_parser.add_argument("--x", default=None)
    present_parser.add_argument("--y", default=None)
    present_parser.add_argument("--width", default=None)
    present_parser.add_argument("--height", default=None)
    add_common_node_opts(present_parser)
    present_parser.add_argument("--timeout", default="10000")
    present_parser.add_argument("--json", action="store_true")

    async def present_action(opts):
        placement = {
            "x": _parse_canvas_finite_number_option(opts.get("x"), "--x"),
            "y": _parse_canvas_finite_number_option(opts.get("y"), "--y"),
            "width": _parse_canvas_finite_number_option(opts.get("width"), "--width"),
            "height": _parse_canvas_finite_number_option(opts.get("height"), "--height"),
        }
        params = {}
        if opts.get("target"):
            params["url"] = opts["target"]
        if any(v is not None for v in placement.values()):
            params["placement"] = placement
        await _invoke_canvas(deps, opts, "canvas.present", params)
        if not opts.get("json"):
            ok = deps["getNodesTheme"]()["ok"]
            deps["defaultRuntime"]["log"](ok("canvas present ok"))

    present_parser.set_defaults(func=present_action)

    hide_parser = canvas_parser.add_parser("hide", help="Hide the canvas")
    add_common_node_opts(hide_parser)
    hide_parser.add_argument("--timeout", default="10000")
    hide_parser.add_argument("--json", action="store_true")

    async def hide_action(opts):
        await _invoke_canvas(deps, opts, "canvas.hide")
        if not opts.get("json"):
            ok = deps["getNodesTheme"]()["ok"]
            deps["defaultRuntime"]["log"](ok("canvas hide ok"))

    hide_parser.set_defaults(func=hide_action)

    navigate_parser = canvas_parser.add_parser("navigate", help="Navigate the canvas to a URL")
    navigate_parser.add_argument("url", help="Target URL/path")
    add_common_node_opts(navigate_parser)
    navigate_parser.add_argument("--timeout", default="10000")
    navigate_parser.add_argument("--json", action="store_true")

    async def navigate_action(opts):
        await _invoke_canvas(deps, opts, "canvas.navigate", {"url": opts["url"]})
        if not opts.get("json"):
            ok = deps["getNodesTheme"]()["ok"]
            deps["defaultRuntime"]["log"](ok("canvas navigate ok"))

    navigate_parser.set_defaults(func=navigate_action)

    eval_parser = canvas_parser.add_parser("eval", help="Evaluate JavaScript in the canvas")
    eval_parser.add_argument("js", nargs="?", default=None, help="JavaScript to evaluate")
    eval_parser.add_argument("--js", default=None, help="JavaScript to evaluate")
    add_common_node_opts(eval_parser)
    eval_parser.add_argument("--timeout", default="10000")
    eval_parser.add_argument("--json", action="store_true")

    async def eval_action(opts):
        js = opts.get("js") or opts.get("js_positional")
        if not js:
            raise ValueError("missing --js or <js>")
        raw = await _invoke_canvas(deps, opts, "canvas.eval", {"javaScript": js})
        if opts.get("json"):
            deps["defaultRuntime"]["writeJson"](raw)
            return
        payload = raw.get("payload") if isinstance(raw, dict) else None
        if isinstance(payload, dict) and payload.get("result"):
            deps["defaultRuntime"]["log"](payload["result"])
        else:
            ok = deps["getNodesTheme"]()["ok"]
            deps["defaultRuntime"]["log"](ok("canvas eval ok"))

    eval_parser.set_defaults(func=eval_action)

    a2ui_parser = canvas_parser.add_parser("a2ui", help="Render A2UI content on the canvas")
    a2ui_sub = a2ui_parser.add_subparsers(dest="a2ui")

    push_parser = a2ui_sub.add_parser("push", help="Push A2UI JSONL to the canvas")
    push_parser.add_argument("--jsonl", default=None, help="Path to JSONL payload")
    push_parser.add_argument("--text", default=None, help="Render a quick A2UI text payload")
    add_common_node_opts(push_parser)
    push_parser.add_argument("--timeout", default="10000")
    push_parser.add_argument("--json", action="store_true")

    async def push_action(opts):
        has_jsonl = bool(opts.get("jsonl"))
        has_text = isinstance(opts.get("text"), str)
        if has_jsonl == has_text:
            raise ValueError("provide exactly one of --jsonl or --text")
        if has_text:
            jsonl = build_a2ui_text_jsonl(opts.get("text", ""))
        else:
            with open(str(opts["jsonl"]), "r", encoding="utf-8") as f:
                jsonl = f.read()
        result = validate_a2ui_jsonl(jsonl)
        if result["version"] == "v0.9":
            raise ValueError("Detected A2UI v0.9 JSONL (createSurface). OpenClaw currently supports v0.8 only.")
        await _invoke_canvas(deps, opts, "canvas.a2ui.pushJSONL", {"jsonl": jsonl})
        if not opts.get("json"):
            ok = deps["getNodesTheme"]()["ok"]
            count = result["messageCount"]
            deps["defaultRuntime"]["log"](ok(f"canvas a2ui push ok (v0.8, {count} message{'s' if count != 1 else ''})"))

    push_parser.set_defaults(func=push_action)

    reset_parser = a2ui_sub.add_parser("reset", help="Reset A2UI renderer state")
    add_common_node_opts(reset_parser)
    reset_parser.add_argument("--timeout", default="10000")
    reset_parser.add_argument("--json", action="store_true")

    async def reset_action(opts):
        await _invoke_canvas(deps, opts, "canvas.a2ui.reset")
        if not opts.get("json"):
            ok = deps["getNodesTheme"]()["ok"]
            deps["defaultRuntime"]["log"](ok("canvas a2ui reset ok"))

    reset_parser.set_defaults(func=reset_action)
