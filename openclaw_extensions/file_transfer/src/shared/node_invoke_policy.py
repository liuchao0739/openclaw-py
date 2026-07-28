from __future__ import annotations

import asyncio
import hashlib
import subprocess
import time
from typing import Any, Literal, TypedDict

from openclaw.plugin_sdk.plugin_entry import (
    OpenClawPluginNodeInvokePolicy,
    OpenClawPluginNodeInvokePolicyContext,
    OpenClawPluginNodeInvokePolicyResult,
)
from openclaw_extensions.file_transfer.shared.audit import (
    FileTransferAuditOp,
    append_file_transfer_audit,
)
from openclaw_extensions.file_transfer.shared.node_invoke_policy_commands import (
    FILE_TRANSFER_NODE_INVOKE_COMMANDS,
    FileTransferNodeInvokeCommand,
)
from openclaw_extensions.file_transfer.shared.params import read_positive_integer_param
from openclaw_extensions.file_transfer.shared.policy import (
    FilePolicyKind,
    evaluate_file_policy,
    persist_allow_always,
)

FILE_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024
FILE_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
DIR_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DIR_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
DIR_FETCH_MAX_ENTRIES = 5000
DIR_FETCH_ARCHIVE_LIST_TIMEOUT_MS = 30_000
DIR_FETCH_ARCHIVE_LIST_MAX_OUTPUT_BYTES = 32 * 1024 * 1024
DIR_FETCH_ARCHIVE_LIST_STDERR_TAIL_CHARS = 4096

FileTransferCommand = FileTransferNodeInvokeCommand


def _as_record(value: Any) -> dict[str, Any]:
    if value and isinstance(value, dict):
        return value
    return {}


def _append_bounded_text_tail(current: str, text: str, max_chars: int) -> str:
    next_text = current + text
    return next_text[-max_chars:] if len(next_text) > max_chars else next_text


def _read_path(params: dict[str, Any]) -> str:
    value = params.get("path")
    return value.strip() if isinstance(value, str) else ""


def _read_max_bytes(
    value: Any,
    default_value: int,
    hard_max: int,
    policy_max: int | None = None,
) -> int:
    if value is None:
        parsed = default_value
    else:
        parsed = read_positive_integer_param({"maxBytes": value}, "maxBytes")
        if parsed is None:
            parsed = default_value
    requested = parsed
    clamped = max(1, min(requested, hard_max))
    if policy_max is not None:
        return min(clamped, policy_max)
    return clamped


def _command_kind(command: FileTransferCommand) -> FilePolicyKind:
    return "write" if command == "file.write" else "read"


def _validate_fetch_max_bytes_param(command: FileTransferCommand, params: dict[str, Any]) -> None:
    if command not in ("file.fetch", "dir.fetch"):
        return
    if "maxBytes" in params:
        read_positive_integer_param(params, "maxBytes")


def _prompt_verb(command: FileTransferCommand) -> str:
    mapping = {
        "dir.fetch": "Fetch directory",
        "dir.list": "List directory",
        "file.write": "Write file",
        "file.fetch": "Read file",
    }
    return mapping.get(command, command)


async def _request_approval(
    ctx: OpenClawPluginNodeInvokePolicyContext,
    op: FileTransferAuditOp,
    kind: FilePolicyKind,
    path: str,
    started_at: float,
) -> dict[str, Any]:
    node_display_name = None
    node_obj = ctx.get("node")
    if isinstance(node_obj, dict):
        node_display_name = node_obj.get("displayName")

    decision = evaluate_file_policy(
        node_id=ctx["nodeId"],
        node_display_name=node_display_name,
        kind=kind,
        path=path,
        plugin_config=ctx.get("pluginConfig"),
    )

    if decision.get("ok") and decision.get("reason") == "matched-allow":
        return {
            "ok": True,
            "followSymlinks": decision.get("followSymlinks", False),
            "maxBytes": decision.get("maxBytes"),
        }

    should_ask = (decision.get("ok") and decision.get("reason") == "ask-always") or (
        not decision.get("ok") and decision.get("askable")
    )

    if not should_ask:
        code_val = decision.get("code", "")
        reason_val = decision.get("reason", "")
        decision_label = "denied:no_policy" if code_val == "NO_POLICY" else "denied:policy"
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": path,
                "decision": decision_label,
                "errorCode": code_val if not decision.get("ok") else None,
                "reason": reason_val,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {
            "ok": False,
            "code": "POLICY_DENIED" if decision.get("ok") else code_val,
            "message": f"{op} {'POLICY_DENIED' if decision.get('ok') else code_val}: {reason_val}",
        }

    approvals = ctx.get("approvals")
    if approvals is None:
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": path,
                "decision": "denied:approval",
                "reason": "plugin approvals unavailable",
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {
            "ok": False,
            "code": "APPROVAL_UNAVAILABLE",
            "message": f"{op} APPROVAL_UNAVAILABLE: plugin approvals unavailable",
        }

    verb = _prompt_verb(op)
    subject = node_display_name or ctx["nodeId"]
    kind_label = "Read" if kind == "read" else "Write"
    approval = await approvals.request(
        {
            "title": f"{verb}: {path}",
            "description": f"Allow {verb.lower()} on {subject}\nPath: {path}\nKind: {kind}\n\n\"allow-always\" appends this exact path to allow{kind_label}Paths.",
            "severity": "warning" if kind == "write" else "info",
            "toolName": op,
        }
    )

    decision_val = approval.get("decision")
    if decision_val in ("deny", None) or not decision_val:
        deny_reason = "operator denied" if decision_val == "deny" else "no operator available"
        deny_code = "APPROVAL_DENIED" if decision_val == "deny" else "APPROVAL_UNAVAILABLE"
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": path,
                "decision": "denied:approval",
                "reason": deny_reason,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {
            "ok": False,
            "code": deny_code,
            "message": f"{op} {deny_code}: {deny_reason}",
        }

    if decision_val == "allow-always":
        try:
            await persist_allow_always(
                node_id=ctx["nodeId"],
                node_display_name=node_display_name,
                kind=kind,
                path=path,
            )
            refreshed = evaluate_file_policy(
                node_id=ctx["nodeId"],
                node_display_name=node_display_name,
                kind=kind,
                path=path,
                plugin_config=ctx.get("pluginConfig"),
            )
            if refreshed.get("ok"):
                await append_file_transfer_audit(
                    {
                        "op": op,
                        "nodeId": ctx["nodeId"],
                        "nodeDisplayName": node_display_name or "",
                        "requestedPath": path,
                        "decision": "allowed:always",
                        "durationMs": int((time.time() - started_at) * 1000),
                    }
                )
                return {
                    "ok": True,
                    "followSymlinks": refreshed.get("followSymlinks", False),
                    "maxBytes": refreshed.get("maxBytes"),
                }
        except Exception as error:
            await append_file_transfer_audit(
                {
                    "op": op,
                    "nodeId": ctx["nodeId"],
                    "nodeDisplayName": node_display_name or "",
                    "requestedPath": path,
                    "decision": "allowed:always",
                    "reason": f"persist failed: {error}",
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            return {
                "ok": True,
                "followSymlinks": decision.get("followSymlinks", False) if decision.get("ok") else False,
                "maxBytes": decision.get("maxBytes"),
            }

    await append_file_transfer_audit(
        {
            "op": op,
            "nodeId": ctx["nodeId"],
            "nodeDisplayName": node_display_name or "",
            "requestedPath": path,
            "decision": "allowed:always" if decision_val == "allow-always" else "allowed:once",
            "durationMs": int((time.time() - started_at) * 1000),
        }
    )
    return {
        "ok": True,
        "followSymlinks": decision.get("followSymlinks", False) if decision.get("ok") else False,
        "maxBytes": decision.get("maxBytes"),
    }


def _prepare_params(
    command: FileTransferCommand,
    params: dict[str, Any],
    follow_symlinks: bool,
    max_bytes: int | None = None,
) -> dict[str, Any]:
    next_params: dict[str, Any] = {
        **params,
        "followSymlinks": follow_symlinks,
    }
    next_params.pop("preflightOnly", None)
    if command == "file.fetch":
        next_params["maxBytes"] = _read_max_bytes(
            params.get("maxBytes"), FILE_FETCH_DEFAULT_MAX_BYTES, FILE_FETCH_HARD_MAX_BYTES, max_bytes
        )
    elif command == "dir.fetch":
        next_params["maxBytes"] = _read_max_bytes(
            params.get("maxBytes"), DIR_FETCH_DEFAULT_MAX_BYTES, DIR_FETCH_HARD_MAX_BYTES, max_bytes
        )
    return next_params


def _read_result_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    payload = result.get("payload")
    if payload and isinstance(payload, dict):
        return payload
    return None


def _join_remote_policy_path(root: str, rel_path: str) -> str:
    rel = rel_path.replace("\\", "/")
    if rel.startswith("./"):
        rel = rel[2:]
    if not rel or rel == ".":
        return root
    sep = "\\" if "\\" in root and "/" not in root else "/"
    clean_root = root.rstrip("\\/")
    prefix = clean_root + sep if clean_root else sep
    return prefix + rel.replace("/", sep)


def _validate_dir_fetch_preflight_entry(entry: str) -> dict[str, Any]:
    if "\0" in entry:
        return {"ok": False, "reason": "entry contains NUL byte"}
    normalized = entry.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized or normalized == ".":
        return {"ok": False, "reason": "entry is empty"}
    if normalized.startswith("/") or (len(normalized) > 1 and normalized[0].isalpha() and normalized[1:3] == ":/"):
        return {"ok": False, "reason": "entry is absolute"}
    if normalized == ".." or normalized.startswith("../") or "/../" in normalized:
        return {"ok": False, "reason": "entry contains '..' traversal"}
    return {"ok": True}


def _normalize_tar_entry_path(entry: str) -> str | None:
    normalized = entry.replace("\\", "/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    normalized = normalized.rstrip("/")
    return normalized if len(normalized) > 0 else None


async def _list_dir_fetch_archive_entries(
    payload: dict[str, Any] | None,
) -> dict[str, Any]:
    tar_base64 = payload.get("tarBase64", "") if payload else ""
    if not tar_base64 or not isinstance(tar_base64, str):
        return {
            "ok": False,
            "code": "ARCHIVE_ENTRIES_MISSING",
            "reason": "dir.fetch archive did not return tarBase64",
        }

    import base64
    tar_buffer = base64.b64decode(tar_base64)

    tar_bin = "/usr/bin/tar" if not _is_windows() else "tar"

    proc = await asyncio.create_subprocess_exec(
        tar_bin, "-tzf", "-",
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )

    entries: list[str] = []
    output_bytes = 0
    stderr_text = ""
    pending = b""

    try:
        stdout_data, stderr_data = await asyncio.wait_for(
            proc.communicate(input=tar_buffer),
            timeout=DIR_FETCH_ARCHIVE_LIST_TIMEOUT_MS / 1000,
        )
        stderr_text = stderr_data.decode("utf-8", errors="replace")

        lines = (pending + stdout_data).split(b"\n")
        pending = lines.pop() if lines else b""
        for line in lines:
            line_str = line.decode("utf-8", errors="replace")
            entry = _normalize_tar_entry_path(line_str)
            if entry is not None:
                entries.append(entry)
                if len(entries) > DIR_FETCH_MAX_ENTRIES:
                    proc.kill()
                    return {
                        "ok": False,
                        "code": "ARCHIVE_ENTRIES_TOO_MANY",
                        "reason": f"dir.fetch archive contains more than {DIR_FETCH_MAX_ENTRIES} entries",
                    }

        if proc.returncode != 0:
            return {
                "ok": False,
                "code": "ARCHIVE_ENTRIES_UNREADABLE",
                "reason": f"tar -tzf exited {proc.returncode}: {stderr_text[-200:]}",
            }

        if pending:
            line_str = pending.decode("utf-8", errors="replace")
            entry = _normalize_tar_entry_path(line_str)
            if entry is not None:
                entries.append(entry)

        return {"ok": True, "entries": entries}
    except asyncio.TimeoutError:
        proc.kill()
        return {
            "ok": False,
            "code": "ARCHIVE_ENTRIES_UNREADABLE",
            "reason": "tar -tzf timed out",
        }
    except Exception as e:
        return {
            "ok": False,
            "code": "ARCHIVE_ENTRIES_UNREADABLE",
            "reason": f"tar -tzf error: {e}",
        }


def _is_windows() -> bool:
    import platform
    return platform.system() == "Windows"


async def _validate_dir_fetch_entries(
    ctx: OpenClawPluginNodeInvokePolicyContext,
    op: FileTransferAuditOp,
    requested_path: str,
    canonical_path: str,
    entries: Any,
    started_at: float,
    phase: Literal["preflight", "archive"],
) -> OpenClawPluginNodeInvokePolicyResult | None:
    node_display_name = None
    node_obj = ctx.get("node")
    if isinstance(node_obj, dict):
        node_display_name = node_obj.get("displayName")

    missing_code = "PREFLIGHT_ENTRIES_MISSING" if phase == "preflight" else "ARCHIVE_ENTRIES_MISSING"
    invalid_code = "PREFLIGHT_ENTRY_INVALID" if phase == "preflight" else "ARCHIVE_ENTRY_INVALID"
    too_many_code = "PREFLIGHT_ENTRIES_TOO_MANY" if phase == "preflight" else "ARCHIVE_ENTRIES_TOO_MANY"

    if not isinstance(entries, list):
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "canonicalPath": canonical_path,
                "decision": "error",
                "errorCode": missing_code,
                "reason": f"dir.fetch {phase} did not return entries",
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return _policy_denied_result(
            op,
            missing_code,
            f"dir.fetch {phase} did not return entries; refusing archive transfer",
            {"path": canonical_path},
        )

    if len(entries) > DIR_FETCH_MAX_ENTRIES:
        reason = f"dir.fetch {phase} contains {len(entries)} entries; limit {DIR_FETCH_MAX_ENTRIES}"
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "canonicalPath": canonical_path,
                "decision": "denied:policy",
                "errorCode": too_many_code,
                "reason": reason,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return _policy_denied_result(
            op,
            too_many_code,
            f"{reason}; refusing archive transfer",
            {"path": canonical_path, "reason": reason},
        )

    validated_entries: list[str] = []
    for entry in entries:
        if not isinstance(entry, str) or len(entry) == 0:
            await append_file_transfer_audit(
                {
                    "op": op,
                    "nodeId": ctx["nodeId"],
                    "nodeDisplayName": node_display_name or "",
                    "requestedPath": requested_path,
                    "canonicalPath": canonical_path,
                    "decision": "denied:policy",
                    "errorCode": invalid_code,
                    "reason": "entry is not a non-empty string",
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            return _policy_denied_result(
                op,
                invalid_code,
                f"directory {phase} entry is invalid: entry is not a non-empty string",
                {"path": canonical_path, "reason": "entry is not a non-empty string"},
            )

        entry_validation = _validate_dir_fetch_preflight_entry(entry)
        if not entry_validation.get("ok"):
            candidate = _join_remote_policy_path(canonical_path, entry)
            await append_file_transfer_audit(
                {
                    "op": op,
                    "nodeId": ctx["nodeId"],
                    "nodeDisplayName": node_display_name or "",
                    "requestedPath": requested_path,
                    "canonicalPath": candidate,
                    "decision": "denied:policy",
                    "errorCode": invalid_code,
                    "reason": entry_validation.get("reason", ""),
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            return _policy_denied_result(
                op,
                invalid_code,
                f"directory {phase} entry {entry} is invalid: {entry_validation.get('reason', '')}",
                {"path": candidate, "reason": entry_validation.get("reason", "")},
            )
        validated_entries.append(entry)

    candidates = [canonical_path]
    for entry in validated_entries:
        candidates.append(_join_remote_policy_path(canonical_path, entry))

    for candidate in candidates:
        policy = evaluate_file_policy(
            node_id=ctx["nodeId"],
            node_display_name=node_display_name,
            kind="read",
            path=candidate,
            plugin_config=ctx.get("pluginConfig"),
        )
        if policy.get("ok"):
            continue
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "canonicalPath": candidate,
                "decision": "denied:policy",
                "errorCode": policy.get("code", ""),
                "reason": policy.get("reason", ""),
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return _policy_denied_result(
            op,
            "PATH_POLICY_DENIED",
            f"directory {phase} entry {candidate} is not allowed by policy: {policy.get('reason', '')}",
            {"path": candidate, "reason": policy.get("reason", "")},
        )

    return None


def _policy_denied_result(
    op: FileTransferAuditOp,
    code: str,
    message: str,
    details: dict[str, Any] | None = None,
) -> OpenClawPluginNodeInvokePolicyResult:
    result: dict[str, Any] = {
        "ok": False,
        "code": code,
        "message": f"{op} {code}: {message}",
    }
    if details:
        result["details"] = details
    return result


async def _invoke_preflight(
    ctx: OpenClawPluginNodeInvokePolicyContext,
    op: FileTransferAuditOp,
    params: dict[str, Any],
    requested_path: str,
    started_at: float,
) -> dict[str, Any]:
    node_display_name = None
    node_obj = ctx.get("node")
    if isinstance(node_obj, dict):
        node_display_name = node_obj.get("displayName")

    preflight = await ctx["invokeNode"](
        {
            "params": {
                **params,
                "preflightOnly": True,
            },
        }
    )

    if not preflight.get("ok"):
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "decision": "error",
                "errorCode": preflight.get("code"),
                "errorMessage": preflight.get("message"),
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {
            "ok": False,
            "result": {
                "ok": False,
                "code": preflight.get("code"),
                "message": f"{op} failed: {preflight.get('message')}",
                "details": preflight.get("details"),
                "unavailable": True,
            },
        }

    payload = _read_result_payload(preflight)
    if payload and payload.get("ok") is False:
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "canonicalPath": payload.get("canonicalPath") if isinstance(payload.get("canonicalPath"), str) else None,
                "decision": "error",
                "errorCode": payload.get("code") if isinstance(payload.get("code"), str) else None,
                "errorMessage": payload.get("message") if isinstance(payload.get("message"), str) else None,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {"ok": False, "result": preflight}

    canonical_path = payload.get("path") if payload and isinstance(payload.get("path"), str) else requested_path
    return {"ok": True, "payload": payload, "canonicalPath": canonical_path}


async def _run_path_preflight(
    ctx: OpenClawPluginNodeInvokePolicyContext,
    op: FileTransferAuditOp,
    kind: FilePolicyKind,
    params: dict[str, Any],
    requested_path: str,
    started_at: float,
) -> OpenClawPluginNodeInvokePolicyResult | None:
    preflight = await _invoke_preflight(ctx, op, params, requested_path, started_at)
    if not preflight.get("ok"):
        return preflight["result"]

    node_display_name = None
    node_obj = ctx.get("node")
    if isinstance(node_obj, dict):
        node_display_name = node_obj.get("displayName")

    canonical_path = preflight["canonicalPath"]
    if canonical_path == requested_path:
        return None

    policy = evaluate_file_policy(
        node_id=ctx["nodeId"],
        node_display_name=node_display_name,
        kind=kind,
        path=canonical_path,
        plugin_config=ctx.get("pluginConfig"),
    )
    if policy.get("ok"):
        return None

    await append_file_transfer_audit(
        {
            "op": op,
            "nodeId": ctx["nodeId"],
            "nodeDisplayName": node_display_name or "",
            "requestedPath": requested_path,
            "canonicalPath": canonical_path,
            "decision": "denied:symlink_escape",
            "errorCode": policy.get("code"),
            "reason": policy.get("reason"),
            "durationMs": int((time.time() - started_at) * 1000),
        }
    )
    return {
        "ok": False,
        "code": "SYMLINK_TARGET_DENIED",
        "message": f"{op} SYMLINK_TARGET_DENIED: requested path resolved to {canonical_path} which is not allowed by policy",
    }


async def _run_dir_fetch_preflight(
    ctx: OpenClawPluginNodeInvokePolicyContext,
    op: FileTransferAuditOp,
    params: dict[str, Any],
    requested_path: str,
    started_at: float,
) -> OpenClawPluginNodeInvokePolicyResult | None:
    preflight = await _invoke_preflight(ctx, op, params, requested_path, started_at)
    if not preflight.get("ok"):
        return preflight["result"]

    return await _validate_dir_fetch_entries(
        ctx=ctx,
        op=op,
        requested_path=requested_path,
        canonical_path=preflight["canonicalPath"],
        entries=preflight["payload"].get("entries") if preflight["payload"] else None,
        started_at=started_at,
        phase="preflight",
    )


async def _handle_file_transfer_invoke(
    ctx: OpenClawPluginNodeInvokePolicyContext,
) -> OpenClawPluginNodeInvokePolicyResult:
    command = ctx.get("command", "")
    if command not in FILE_TRANSFER_NODE_INVOKE_COMMANDS:
        return {"ok": False, "code": "UNSUPPORTED_COMMAND", "message": "unsupported file-transfer command"}

    op: FileTransferAuditOp = command
    params = _as_record(ctx.get("params"))
    requested_path = _read_path(params)
    node_display_name = None
    node_obj = ctx.get("node")
    if isinstance(node_obj, dict):
        node_display_name = node_obj.get("displayName")
    started_at = time.time()

    if not requested_path:
        return {"ok": False, "code": "INVALID_PARAMS", "message": f"{op} path required"}

    try:
        _validate_fetch_max_bytes_param(command, params)
    except Exception as error:
        return {
            "ok": False,
            "code": "INVALID_PARAMS",
            "message": str(error),
        }

    gate = await _request_approval(
        ctx=ctx,
        op=op,
        kind=_command_kind(command),
        path=requested_path,
        started_at=started_at,
    )
    if not gate.get("ok"):
        return {"ok": False, "code": gate.get("code"), "message": gate.get("message")}

    try:
        forwarded_params = _prepare_params(
            command,
            params,
            gate.get("followSymlinks", False),
            gate.get("maxBytes"),
        )
    except Exception as error:
        return {
            "ok": False,
            "code": "INVALID_PARAMS",
            "message": str(error),
        }

    if command == "file.fetch":
        preflight_deny = await _run_path_preflight(
            ctx, op, "read", forwarded_params, requested_path, started_at
        )
        if preflight_deny:
            return preflight_deny
    elif command == "file.write":
        preflight_deny = await _run_path_preflight(
            ctx, op, "write", forwarded_params, requested_path, started_at
        )
        if preflight_deny:
            return preflight_deny
    elif command == "dir.fetch":
        preflight_deny = await _run_dir_fetch_preflight(
            ctx, op, forwarded_params, requested_path, started_at
        )
        if preflight_deny:
            return preflight_deny

    result = await ctx["invokeNode"]({"params": forwarded_params})
    if not result.get("ok"):
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "decision": "error",
                "errorCode": result.get("code"),
                "errorMessage": result.get("message"),
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return {
            "ok": False,
            "code": result.get("code"),
            "message": f"{op} failed: {result.get('message')}",
            "details": result.get("details"),
            "unavailable": True,
        }

    payload = _read_result_payload(result)
    if payload and payload.get("ok") is False:
        await append_file_transfer_audit(
            {
                "op": op,
                "nodeId": ctx["nodeId"],
                "nodeDisplayName": node_display_name or "",
                "requestedPath": requested_path,
                "canonicalPath": payload.get("canonicalPath") if isinstance(payload.get("canonicalPath"), str) else None,
                "decision": "error",
                "errorCode": payload.get("code") if isinstance(payload.get("code"), str) else None,
                "errorMessage": payload.get("message") if isinstance(payload.get("message"), str) else None,
                "durationMs": int((time.time() - started_at) * 1000),
            }
        )
        return result

    canonical_path = payload.get("path") if payload and isinstance(payload.get("path"), str) else requested_path
    if canonical_path != requested_path:
        postflight = evaluate_file_policy(
            node_id=ctx["nodeId"],
            node_display_name=node_display_name,
            kind=_command_kind(command),
            path=canonical_path,
            plugin_config=ctx.get("pluginConfig"),
        )
        if not postflight.get("ok"):
            await append_file_transfer_audit(
                {
                    "op": op,
                    "nodeId": ctx["nodeId"],
                    "nodeDisplayName": node_display_name or "",
                    "requestedPath": requested_path,
                    "canonicalPath": canonical_path,
                    "decision": "denied:symlink_escape",
                    "errorCode": postflight.get("code"),
                    "reason": postflight.get("reason"),
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            return {
                "ok": False,
                "code": "SYMLINK_TARGET_DENIED",
                "message": f"{op} SYMLINK_TARGET_DENIED: requested path resolved to {canonical_path} which is not allowed by policy",
            }

    if command == "dir.fetch":
        archive_result = await _list_dir_fetch_archive_entries(payload)
        if not archive_result.get("ok"):
            await append_file_transfer_audit(
                {
                    "op": op,
                    "nodeId": ctx["nodeId"],
                    "nodeDisplayName": node_display_name or "",
                    "requestedPath": requested_path,
                    "canonicalPath": canonical_path,
                    "decision": "error",
                    "errorCode": archive_result.get("code"),
                    "reason": archive_result.get("reason"),
                    "durationMs": int((time.time() - started_at) * 1000),
                }
            )
            return _policy_denied_result(
                op,
                archive_result.get("code", "UNKNOWN"),
                f"{archive_result.get('reason', '')}; refusing archive transfer",
                {"path": canonical_path, "reason": archive_result.get("reason", "")},
            )

        archive_deny = await _validate_dir_fetch_entries(
            ctx=ctx,
            op=op,
            requested_path=requested_path,
            canonical_path=canonical_path,
            entries=archive_result.get("entries", []),
            started_at=started_at,
            phase="archive",
        )
        if archive_deny:
            return archive_deny

    size_val = payload.get("size") if payload else None
    sha_val = payload.get("sha256") if payload else None
    await append_file_transfer_audit(
        {
            "op": op,
            "nodeId": ctx["nodeId"],
            "nodeDisplayName": node_display_name or "",
            "requestedPath": requested_path,
            "canonicalPath": canonical_path,
            "decision": "allowed",
            "sizeBytes": size_val if isinstance(size_val, int) else None,
            "sha256": sha_val if isinstance(sha_val, str) else None,
            "durationMs": int((time.time() - started_at) * 1000),
        }
    )

    return result


def create_file_transfer_node_invoke_policy() -> OpenClawPluginNodeInvokePolicy:
    return {
        "commands": list(FILE_TRANSFER_NODE_INVOKE_COMMANDS),
        "handle": _handle_file_transfer_invoke,
    }