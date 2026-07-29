import base64
import os
import uuid
from pathlib import Path
from typing import Any, Optional

from .cli_helpers import normalize_canvas_snapshot_file_extension, parse_canvas_snapshot_payload
from .tool_schema import CanvasToolSchema


def _resolve_preferred_openclaw_tmp_dir() -> str:
    tmp_dir = os.environ.get("OPENCLAW_TMP_DIR") or os.environ.get("TMPDIR") or "/tmp"
    return str(Path(tmp_dir))


def _read_string_param(params: dict, key: str, required: bool = False, trim: bool = False, label: str = None) -> Optional[str]:
    value = params.get(key)
    if value is None:
        if required:
            raise ValueError(f"missing required parameter: {label or key}")
        return None
    if not isinstance(value, str):
        value = str(value)
    if trim:
        value = value.strip()
    return value


def _read_finite_number_param(params: dict, key: str, min_val: float = None, max_val: float = None) -> Optional[float]:
    value = params.get(key)
    if value is None:
        return None
    try:
        num = float(value)
    except (ValueError, TypeError):
        return None
    if min_val is not None and num < min_val:
        return None
    if max_val is not None and num > max_val:
        return None
    return num


def _read_positive_integer_param(params: dict, key: str) -> Optional[int]:
    value = params.get(key)
    if value is None:
        return None
    try:
        num = int(value)
    except (ValueError, TypeError):
        return None
    if num > 0:
        return num
    return None


def _read_gateway_call_options(params: dict) -> dict:
    return {
        "gatewayUrl": _read_string_param(params, "gatewayUrl", trim=False),
        "gatewayToken": _read_string_param(params, "gatewayToken", trim=False),
        "timeoutMs": _read_positive_integer_param(params, "timeoutMs"),
    }


async def _list_nodes(opts: dict) -> list:
    return []


async def _resolve_node_id_from_list(nodes: list, query: Optional[str], allow_default: bool = False) -> str:
    if not nodes:
        raise ValueError("no nodes available")
    if not query and allow_default and nodes:
        return nodes[0].get("nodeId", "")
    for node in nodes:
        node_id = node.get("nodeId", "")
        if query and (node_id == query or node.get("displayName", "") == query or node.get("remoteIp", "") == query):
            return node_id
    if allow_default:
        return nodes[0].get("nodeId", "")
    raise ValueError(f"no matching node for query: {query}")


async def _resolve_node_id(opts: dict, query: Optional[str] = None, allow_default: bool = False) -> str:
    nodes = await _list_nodes(opts)
    return await _resolve_node_id_from_list(nodes, query, allow_default)


async def _call_gateway_tool(method: str, opts: dict, params: dict) -> Any:
    return {"payload": {}}


async def _write_base64_to_temp_file(base64_data: str, ext: str) -> str:
    dir_path = _resolve_preferred_openclaw_tmp_dir()
    Path(dir_path).mkdir(parents=True, exist_ok=True, mode=0o700)
    file_ext = "." + normalize_canvas_snapshot_file_extension(ext)
    file_path = os.path.join(dir_path, f"openclaw-canvas-snapshot-{uuid.uuid4()}{file_ext}")
    with open(file_path, "wb") as f:
        f.write(base64.b64decode(base64_data))
    return file_path


def _is_path_inside_root(root: str, candidate: str) -> bool:
    relative = os.path.relpath(candidate, root)
    return relative == "." or (not relative.startswith("..") and not os.path.isabs(relative))


async def _read_jsonl_from_path(jsonl_path: str, workspace_dir: Optional[str] = None) -> str:
    trimmed = jsonl_path.strip()
    if not trimmed:
        return ""
    workspace_root = os.path.abspath(workspace_dir or os.getcwd())
    resolved = os.path.abspath(os.path.join(workspace_root, trimmed))
    workspace_real = os.path.realpath(workspace_root)
    resolved_real = os.path.realpath(resolved)
    if not _is_path_inside_root(workspace_real, resolved_real):
        raise ValueError("jsonlPath outside workspace")
    with open(resolved_real, "r", encoding="utf-8") as f:
        return f.read()


def _resolve_canvas_image_sanitization_limits(config: Any = None) -> dict:
    if isinstance(config, dict):
        agents = config.get("agents", {})
        if isinstance(agents, dict):
            defaults = agents.get("defaults", {})
            if isinstance(defaults, dict):
                configured = defaults.get("imageMaxDimensionPx")
                if isinstance(configured, (int, float)):
                    return {"maxDimensionPx": max(1, int(configured))}
    return {}


def _json_result(data: dict) -> dict:
    import json
    return {
        "content": [{"type": "text", "text": json.dumps(data)}],
        "details": data,
    }


async def _image_result_from_file(label: str, path: str, details: dict = None, image_sanitization: dict = None) -> dict:
    return {
        "content": [{"type": "image", "path": path, "label": label}],
        "details": details or {},
    }


def create_canvas_tool(config: Any = None, workspace_dir: Optional[str] = None) -> dict:
    image_sanitization = _resolve_canvas_image_sanitization_limits(config)

    async def execute(tool_call_id: str, args: dict) -> dict:
        params = args if isinstance(args, dict) else {}
        action = _read_string_param(params, "action", required=True)
        gateway_opts = _read_gateway_call_options(params)

        node_id = await _resolve_node_id(
            gateway_opts,
            _read_string_param(params, "node", trim=True),
            True,
        )

        async def invoke(command: str, invoke_params: dict = None):
            return await _call_gateway_tool("node.invoke", gateway_opts, {
                "nodeId": node_id,
                "command": command,
                "params": invoke_params,
                "idempotencyKey": str(uuid.uuid4()),
            })

        if action == "present":
            placement = {
                "x": _read_finite_number_param(params, "x"),
                "y": _read_finite_number_param(params, "y"),
                "width": _read_finite_number_param(params, "width"),
                "height": _read_finite_number_param(params, "height"),
            }
            invoke_params: dict = {}
            present_target = (
                _read_string_param(params, "target", trim=True)
                or _read_string_param(params, "url", trim=True)
            )
            if present_target:
                invoke_params["url"] = present_target
            if any(v is not None for v in placement.values()):
                invoke_params["placement"] = placement
            await invoke("canvas.present", invoke_params)
            return _json_result({"ok": True})

        if action == "hide":
            await invoke("canvas.hide")
            return _json_result({"ok": True})

        if action == "navigate":
            url = (
                _read_string_param(params, "url", trim=True)
                or _read_string_param(params, "target", required=True, trim=True, label="url")
            )
            await invoke("canvas.navigate", {"url": url})
            return _json_result({"ok": True})

        if action == "eval":
            java_script = _read_string_param(params, "javaScript", required=True)
            raw = await invoke("canvas.eval", {"javaScript": java_script})
            result = None
            if isinstance(raw, dict):
                payload = raw.get("payload", {})
                if isinstance(payload, dict):
                    result = payload.get("result")
            if result:
                return {
                    "content": [{"type": "text", "text": result}],
                    "details": {"result": result},
                }
            return _json_result({"ok": True})

        if action == "snapshot":
            output_format_raw = params.get("outputFormat")
            if isinstance(output_format_raw, str) and output_format_raw.strip():
                format_raw = output_format_raw.strip().lower()
            else:
                format_raw = "png"
            fmt = "jpeg" if format_raw in ("jpg", "jpeg") else "png"
            max_width = _read_positive_integer_param(params, "maxWidth")
            quality = _read_finite_number_param(params, "quality", min_val=0, max_val=1)
            raw = await invoke("canvas.snapshot", {
                "format": fmt,
                "maxWidth": max_width,
                "quality": quality,
            })
            payload = parse_canvas_snapshot_payload(raw.get("payload") if isinstance(raw, dict) else None)
            file_path = await _write_base64_to_temp_file(
                payload["base64"],
                "jpg" if payload["format"] == "jpeg" else payload["format"],
            )
            return await _image_result_from_file(
                label="canvas:snapshot",
                path=file_path,
                details={"format": payload["format"]},
                image_sanitization=image_sanitization,
            )

        if action == "a2ui_push":
            jsonl = ""
            if isinstance(params.get("jsonl"), str) and params["jsonl"].strip():
                jsonl = params["jsonl"]
            elif isinstance(params.get("jsonlPath"), str) and params["jsonlPath"].strip():
                jsonl = await _read_jsonl_from_path(params["jsonlPath"], workspace_dir)
            if not jsonl.strip():
                raise ValueError("jsonl or jsonlPath required")
            await invoke("canvas.a2ui.pushJSONL", {"jsonl": jsonl})
            return _json_result({"ok": True})

        if action == "a2ui_reset":
            await invoke("canvas.a2ui.reset")
            return _json_result({"ok": True})

        raise ValueError(f"Unknown action: {action}")

    return {
        "label": "Canvas",
        "name": "canvas",
        "description": "Control node canvases (present/hide/navigate/eval/snapshot/A2UI). Use snapshot to capture the rendered UI.",
        "parameters": CanvasToolSchema,
        "execute": execute,
    }
