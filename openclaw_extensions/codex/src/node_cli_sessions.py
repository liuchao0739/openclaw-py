import asyncio
import json
import os
import re
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Any, List, Optional

CODEX_CLI_SESSIONS_LIST_COMMAND = "codex.cli.sessions.list"
CODEX_CLI_SESSION_RESUME_COMMAND = "codex.cli.session.resume"

DEFAULT_SESSION_LIMIT = 10
MAX_SESSION_LIMIT = 50
DEFAULT_RESUME_TIMEOUT_MS = 20 * 60_000
SESSION_ID_PATTERN = re.compile(r"^[A-Za-z0-9._:-]{1,128}$")
_active_resume_sessions: set = set()


def create_codex_cli_session_node_host_commands() -> list:
    return [
        {
            "command": CODEX_CLI_SESSIONS_LIST_COMMAND,
            "cap": "codex-cli-sessions",
            "handle": _list_local_codex_cli_sessions,
        },
        {
            "command": CODEX_CLI_SESSION_RESUME_COMMAND,
            "cap": "codex-cli-sessions",
            "dangerous": True,
            "handle": _resume_local_codex_cli_session,
        },
    ]


def create_codex_cli_session_node_invoke_policies() -> list:
    return [
        {
            "commands": [CODEX_CLI_SESSIONS_LIST_COMMAND],
            "defaultPlatforms": ["macos", "linux", "windows"],
            "handle": lambda ctx: ctx["invokeNode"](),
        },
        {
            "commands": [CODEX_CLI_SESSION_RESUME_COMMAND],
            "dangerous": True,
            "handle": lambda ctx: ctx["invokeNode"](),
        },
    ]


async def list_codex_cli_sessions_on_node(params: dict) -> dict:
    node = await _resolve_codex_cli_node({
        "runtime": params["runtime"],
        "requestedNode": params.get("requestedNode"),
        "command": CODEX_CLI_SESSIONS_LIST_COMMAND,
    })
    raw = await params["runtime"]["nodes"]["invoke"]({
        "nodeId": _read_node_id(node),
        "command": CODEX_CLI_SESSIONS_LIST_COMMAND,
        "params": {"limit": params.get("limit"), "filter": params.get("filter")},
        "timeoutMs": 15_000,
    })
    return {"node": node, "result": _parse_codex_cli_sessions_list_result(raw)}


async def resolve_codex_cli_session_for_binding_on_node(params: dict) -> dict:
    listing = await list_codex_cli_sessions_on_node({
        "runtime": params["runtime"],
        "requestedNode": params["requestedNode"],
        "filter": params["sessionId"],
        "limit": MAX_SESSION_LIMIT,
    })
    commands = listing["node"].get("commands") or []
    if CODEX_CLI_SESSION_RESUME_COMMAND not in commands:
        raise Error(f"Node {_format_node_label(listing['node'])} does not expose {CODEX_CLI_SESSION_RESUME_COMMAND}.")
    session = next((s for s in listing["result"]["sessions"] if s["sessionId"] == params["sessionId"]), None)
    return {"node": listing["node"], "session": session}


async def resume_codex_cli_session_on_node(params: dict) -> dict:
    raw = await params["runtime"]["nodes"]["invoke"]({
        "nodeId": params["nodeId"],
        "command": CODEX_CLI_SESSION_RESUME_COMMAND,
        "params": {
            "sessionId": params["sessionId"],
            "prompt": params["prompt"],
            "cwd": params.get("cwd"),
            "timeoutMs": params.get("timeoutMs"),
        },
        "timeoutMs": (params.get("timeoutMs") or DEFAULT_RESUME_TIMEOUT_MS) + 5_000,
    })
    payload = _unwrap_node_invoke_payload(raw)
    if not isinstance(payload, dict) or payload.get("ok") is not True or not isinstance(payload.get("text"), str):
        raise Error("Codex CLI resume returned an invalid payload.")
    return {
        "ok": True,
        "sessionId": payload["sessionId"] if isinstance(payload.get("sessionId"), str) else params["sessionId"],
        "text": payload["text"],
    }


def format_codex_cli_sessions(params: dict) -> str:
    from .command_formatters import format_codex_display_text

    if not params["result"]["sessions"]:
        return f"No Codex CLI sessions returned from {format_codex_display_text(_format_node_label(params['node']))}."
    lines = [f"Codex CLI sessions on {format_codex_display_text(_format_node_label(params['node']))}:"]
    for session in params["result"]["sessions"]:
        details = [v for v in [session.get("cwd"), session.get("updatedAt")] if v]
        detail_str = f" ({', '.join(format_codex_display_text(d) for d in details)})" if details else ""
        last_msg = f" - {format_codex_display_text(session['lastMessage'])}" if session.get("lastMessage") else ""
        lines.append(
            f"- {format_codex_display_text(session['sessionId'])}{last_msg}{detail_str}\n"
            f"  Bind: /codex resume {format_codex_display_text(session['sessionId'])} --host {format_codex_display_text(_read_node_id(params['node']))} --bind here"
        )
    return "\n".join(lines)


async def _list_local_codex_cli_sessions(params_json: Optional[str] = None) -> str:
    params = _read_record_param(params_json)
    limit = _normalize_limit(params.get("limit"))
    filter_text = params.get("filter", "").strip().lower() if isinstance(params.get("filter"), str) else ""
    codex_home = _resolve_codex_home()
    summaries = await _read_history_sessions(codex_home)
    await _hydrate_session_files(codex_home, summaries)
    await _hydrate_sessions_from_session_files(codex_home, summaries)
    sessions = [
        session
        for session in summaries.values()
        if not filter_text
        or any(
            (value or "").lower().find(filter_text) >= 0
            for value in [session["sessionId"], session.get("cwd"), session.get("lastMessage")]
        )
    ]
    sessions.sort(key=lambda s: s.get("updatedAt") or "", reverse=True)
    sessions = sessions[:limit]
    return json.dumps({"sessions": sessions, "codexHome": codex_home})


async def _resume_local_codex_cli_session(params_json: Optional[str] = None) -> str:
    params = _read_record_param(params_json)
    session_id = params.get("sessionId", "").strip() if isinstance(params.get("sessionId"), str) else ""
    prompt = params.get("prompt", "").strip() if isinstance(params.get("prompt"), str) else ""
    if not session_id or not SESSION_ID_PATTERN.match(session_id):
        raise Error("Missing or invalid Codex CLI session id.")
    if not prompt:
        raise Error("Missing Codex CLI prompt.")
    if session_id in _active_resume_sessions:
        raise Error(f"Codex CLI session {session_id} already has an active resume turn.")
    _active_resume_sessions.add(session_id)
    try:
        cwd = params.get("cwd", "").strip() if isinstance(params.get("cwd"), str) and params.get("cwd", "").strip() else None
        text = await _run_codex_exec_resume({
            "sessionId": session_id,
            "prompt": prompt,
            "cwd": cwd,
            "timeoutMs": _normalize_timeout_ms(params.get("timeoutMs")),
        })
        return json.dumps({
            "ok": True,
            "sessionId": session_id,
            "text": text.strip() or "Codex completed without a text reply.",
        })
    finally:
        _active_resume_sessions.discard(session_id)


async def _run_codex_exec_resume(params: dict) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="openclaw-codex-cli-", dir=_resolve_preferred_openclaw_tmp_dir())
    output_path = str(Path(tmp_dir, "last-message.txt"))
    try:
        args = [
            "exec", "resume", "--skip-git-repo-check", "--output-last-message", output_path, params["sessionId"], "-",
        ]
        invocation = _resolve_codex_cli_resume_spawn_invocation(args)
        proc = await asyncio.create_subprocess_exec(
            invocation["command"],
            *invocation["args"],
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=params.get("cwd") or os.getcwd(),
            env=os.environ.copy(),
        )
        timed_out = False
        try:
            stdout_data, stderr_data = await asyncio.wait_for(proc.communicate(params["prompt"].encode("utf-8")), timeout=params["timeoutMs"] / 1000)
        except asyncio.TimeoutError:
            timed_out = True
            proc.kill()
            await proc.wait()
            stdout_data, stderr_data = b"", b""
        if timed_out:
            raise Error(f"codex exec resume timed out after {params['timeoutMs']}ms")
        if proc.returncode != 0:
            message = stderr_data.decode("utf-8").strip() or stdout_data.decode("utf-8").strip() or f"codex exec resume exited with code {proc.returncode}"
            raise Error(message)
        return Path(output_path).read_text(encoding="utf-8")
    finally:
        import shutil

        shutil.rmtree(tmp_dir, ignore_errors=True)


def _resolve_codex_cli_resume_spawn_invocation(args: list) -> dict:
    return {"command": "codex", "args": args, "shell": False}


async def _read_history_sessions(codex_home: str) -> dict:
    summaries: dict = {}
    history_path = str(Path(codex_home, "history.jsonl"))
    content = await _read_file_if_exists(history_path)
    if not content:
        return summaries
    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        try:
            parsed = json.loads(trimmed)
        except ValueError:
            continue
        if not isinstance(parsed, dict) or not isinstance(parsed.get("session_id"), str):
            continue
        session_id = parsed["session_id"].strip()
        if not session_id:
            continue
        entry = summaries.get(session_id) or {"sessionId": session_id, "messageCount": 0}
        entry["messageCount"] += 1
        if isinstance(parsed.get("text"), str) and parsed["text"].strip():
            entry["lastMessage"] = _truncate_text(parsed["text"].strip(), 140)
        if isinstance(parsed.get("ts"), (int, float)):
            entry["updatedAt"] = _timestamp_ms_to_iso_string(parsed["ts"] * 1000) or entry.get("updatedAt")
        summaries[session_id] = entry
    return summaries


async def _hydrate_session_files(codex_home: str, summaries: dict) -> None:
    if not summaries:
        return
    sessions_dir = str(Path(codex_home, "sessions"))
    files = await _find_session_files(sessions_dir, 4)
    pending = set(summaries.keys())
    for file in files:
        basename = Path(file).name
        session_id = next((sid for sid in pending if sid in basename), None)
        if not session_id:
            continue
        entry = summaries.get(session_id)
        if not entry:
            continue
        entry["sessionFile"] = file
        first_line = (await _read_first_line(file)) or ""
        cwd = _read_session_meta_cwd(first_line)
        if cwd:
            entry["cwd"] = cwd
        pending.discard(session_id)
        if not pending:
            return


async def _hydrate_sessions_from_session_files(codex_home: str, summaries: dict) -> None:
    sessions_dir = str(Path(codex_home, "sessions"))
    files = await _find_session_files(sessions_dir, 4)
    for file in files:
        summary = await _read_session_file_summary(file)
        if not summary:
            continue
        existing = summaries.get(summary["sessionId"])
        summaries[summary["sessionId"]] = {
            **summary,
            **(existing or {}),
            "cwd": (existing or {}).get("cwd", summary.get("cwd")),
            "sessionFile": (existing or {}).get("sessionFile", summary.get("sessionFile")),
            "updatedAt": (existing or {}).get("updatedAt", summary.get("updatedAt")),
            "lastMessage": (existing or {}).get("lastMessage", summary.get("lastMessage")),
            "messageCount": (existing or {}).get("messageCount", summary.get("messageCount", 0)),
        }


async def _read_session_file_summary(file: str) -> Optional[dict]:
    content = await _read_file_if_exists(file)
    if not content:
        return None
    session_id = ""
    cwd: Optional[str] = None
    updated_at: Optional[str] = None
    last_message: Optional[str] = None
    message_count = 0
    for line in content.splitlines():
        trimmed = line.strip()
        if not trimmed:
            continue
        try:
            parsed = json.loads(trimmed)
        except ValueError:
            continue
        if not isinstance(parsed, dict):
            continue
        if isinstance(parsed.get("timestamp"), str) and parsed["timestamp"].strip():
            updated_at = parsed["timestamp"].strip()
        if parsed.get("type") == "session_meta" and isinstance(parsed.get("payload"), dict):
            payload = parsed["payload"]
            if isinstance(payload.get("id"), str) and payload["id"].strip():
                session_id = payload["id"].strip()
            if isinstance(payload.get("cwd"), str) and payload["cwd"].strip():
                cwd = payload["cwd"].strip()
            continue
        message_text = _read_response_item_message_text(parsed)
        if message_text:
            message_count += 1
            last_message = _truncate_text(message_text, 140)
    if not session_id:
        session_id = _read_session_id_from_filename(file) or ""
    if not session_id:
        return None
    return {
        "sessionId": session_id,
        "updatedAt": updated_at or (await _read_file_mtime_iso(file)),
        "lastMessage": last_message,
        "cwd": cwd,
        "sessionFile": file,
        "messageCount": message_count,
    }


async def _find_session_files(dir_path: str, max_depth: int) -> List[str]:
    if max_depth < 0:
        return []
    try:
        entries = list(Path(dir_path).iterdir())
    except OSError:
        return []
    files: List[str] = []
    for entry in entries:
        if entry.is_dir():
            files.extend(await _find_session_files(str(entry), max_depth - 1))
        elif entry.is_file() and entry.name.endswith(".jsonl"):
            files.append(str(entry))
    return files


def _read_session_meta_cwd(line: str) -> Optional[str]:
    try:
        parsed = json.loads(line)
    except ValueError:
        return None
    if not isinstance(parsed, dict) or parsed.get("type") != "session_meta" or not isinstance(parsed.get("payload"), dict):
        return None
    cwd = parsed["payload"].get("cwd")
    return cwd.strip() if isinstance(cwd, str) and cwd.strip() else None


def _read_response_item_message_text(parsed: dict) -> Optional[str]:
    if parsed.get("type") != "response_item" or not isinstance(parsed.get("payload"), dict):
        return None
    payload = parsed["payload"]
    if payload.get("type") != "message":
        return None
    role = payload.get("role") if isinstance(payload.get("role"), str) else ""
    if role != "user":
        return None
    content = payload.get("content") if isinstance(payload.get("content"), list) else []
    parts = []
    for entry in content:
        if not isinstance(entry, dict):
            continue
        text = entry.get("text") if isinstance(entry.get("text"), str) else (entry.get("input_text") if isinstance(entry.get("input_text"), str) else None)
        if text and text.strip():
            parts.append(text.strip())
    return " ".join(parts) if parts else None


def _read_session_id_from_filename(file: str) -> Optional[str]:
    match = re.search(r"[0-9a-f]{8}-[0-9a-f-]{27,}", Path(file).name, re.IGNORECASE)
    return match.group(0) if match else None


async def _resolve_codex_cli_node(params: dict) -> dict:
    runtime_nodes = params["runtime"]["nodes"]
    nodes_list = await runtime_nodes["list"]({"connected": True} if not params.get("requestedNode") else None)
    requested = params.get("requestedNode", "").strip() if params.get("requestedNode") else None
    candidates = [
        node for node in nodes_list["nodes"]
        if (requested and any(node.get(field) == requested for field in ["nodeId", "displayName", "remoteIp"]))
        or (not requested and node.get("connected") is True and params["command"] in (node.get("commands") or []))
    ]
    if not candidates:
        raise Error(f"Codex CLI node {requested} was not found." if requested else "No connected node exposes Codex CLI session commands.")
    usable = [node for node in candidates if params["command"] in (node.get("commands") or [])]
    if not usable:
        raise Error(f"Node {requested or 'candidate'} does not expose {params['command']}.")
    if len(usable) > 1:
        raise Error("Multiple Codex CLI-capable nodes connected. Pass --host <node-id>.")
    return usable[0]


def _parse_codex_cli_sessions_list_result(raw) -> dict:
    payload = _unwrap_node_invoke_payload(raw)
    if not isinstance(payload, dict) or not isinstance(payload.get("sessions"), list):
        raise Error("Codex CLI session list returned an invalid payload.")
    sessions = []
    for entry in payload["sessions"]:
        if not isinstance(entry, dict) or not isinstance(entry.get("sessionId"), str):
            continue
        sessions.append({
            "sessionId": entry["sessionId"],
            "updatedAt": entry["updatedAt"] if isinstance(entry.get("updatedAt"), str) else None,
            "lastMessage": entry["lastMessage"] if isinstance(entry.get("lastMessage"), str) else None,
            "cwd": entry["cwd"] if isinstance(entry.get("cwd"), str) else None,
            "sessionFile": entry["sessionFile"] if isinstance(entry.get("sessionFile"), str) else None,
            "messageCount": entry["messageCount"] if isinstance(entry.get("messageCount"), (int, float)) else 0,
        })
    return {"codexHome": payload.get("codexHome", "") if isinstance(payload.get("codexHome"), str) else "", "sessions": sessions}


def _unwrap_node_invoke_payload(raw):
    record = raw if isinstance(raw, dict) else {}
    payload_json = record.get("payloadJSON")
    if isinstance(payload_json, str) and payload_json.strip():
        try:
            return json.loads(payload_json)
        except ValueError as error:
            raise Error("Codex CLI node command returned malformed payloadJSON.") from error
    if "payload" in record:
        return record["payload"]
    return raw


def _read_record_param(params_json: Optional[str]) -> dict:
    if not params_json or not params_json.strip():
        return {}
    try:
        parsed = json.loads(params_json)
        return parsed if isinstance(parsed, dict) else {}
    except ValueError:
        return {}


def _resolve_codex_home() -> str:
    return os.environ.get("CODEX_HOME", "").strip() or str(Path.home() / ".codex")


async def _read_file_if_exists(file: str) -> Optional[str]:
    try:
        return Path(file).read_text(encoding="utf-8")
    except OSError:
        return None


async def _read_first_line(file: str) -> Optional[str]:
    content = await _read_file_if_exists(file)
    if not content:
        return None
    return content.splitlines()[0] if content.splitlines() else ""


async def _read_file_mtime_iso(file: str) -> Optional[str]:
    try:
        import datetime

        return datetime.datetime.fromtimestamp(Path(file).stat().st_mtime, tz=datetime.timezone.utc).isoformat()
    except OSError:
        return None


def _normalize_limit(value) -> int:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return min(MAX_SESSION_LIMIT, max(1, int(value)))
    return DEFAULT_SESSION_LIMIT


def _normalize_timeout_ms(value) -> int:
    if isinstance(value, (int, float)) and not isinstance(value, bool) and value > 0:
        return min(60 * 60_000, int(value))
    return DEFAULT_RESUME_TIMEOUT_MS


def _truncate_text(value: str, max_len: int) -> str:
    return value if len(value) <= max_len else f"{value[:max_len - 3]}..."


def _read_node_id(node: dict) -> str:
    if not node.get("nodeId"):
        raise Error("Codex CLI node did not include a node id.")
    return node["nodeId"]


def _format_node_label(node: dict) -> str:
    return " / ".join(v for v in [node.get("displayName"), node.get("nodeId"), node.get("remoteIp")] if v) or "node"


def _resolve_preferred_openclaw_tmp_dir() -> str:
    from openclaw.plugin_sdk.temp_path import resolve_preferred_openclaw_tmp_dir

    return resolve_preferred_openclaw_tmp_dir()


def _timestamp_ms_to_iso_string(ts_ms):
    import datetime

    try:
        return datetime.datetime.fromtimestamp(ts_ms / 1000, tz=datetime.timezone.utc).isoformat()
    except (ValueError, OSError):
        return None


class Error(Exception):
    pass
