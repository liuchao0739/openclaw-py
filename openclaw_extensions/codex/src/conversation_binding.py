import asyncio
import os
import re
from typing import Optional

from openclaw.plugin_sdk.agent_harness_runtime import format_error_message, resolve_sandbox_context
from openclaw.plugin_sdk.agent_runtime import resolve_session_agent_ids
from openclaw.plugin_sdk.exec_approvals_runtime import load_exec_approvals
from openclaw.plugin_sdk.session_store_runtime import get_session_entry, resolve_store_path

from .app_server.app_server_policy import resolve_codex_app_server_for_model_provider
from .app_server.auth_bridge import resolve_codex_app_server_auth_profile_id_for_agent
from .app_server.capabilities import CODEX_CONTROL_METHODS
from .app_server.config import (
    can_use_codex_model_backed_approvals_reviewer_for_model,
    codex_sandbox_policy_for_turn,
    resolve_codex_app_server_runtime_options,
    resolve_open_claw_exec_policy_for_codex_app_server,
)
from .app_server.protocol_validators import assert_codex_thread_start_response
from .app_server.sandbox_guard import (
    resolve_codex_native_execution_block,
    resolve_codex_native_sandbox_block,
)
from .app_server.session_binding import (
    clear_codex_app_server_binding,
    is_codex_app_server_native_auth_profile,
    normalize_codex_app_server_binding_model_provider,
    read_codex_app_server_binding,
    write_codex_app_server_binding,
)
from .app_server.shared_client import (
    get_leased_shared_codex_app_server_client,
    release_leased_shared_codex_app_server_client,
)
from .app_server.thread_lifecycle import (
    CODEX_NATIVE_PERSONALITY_NONE,
    resolve_codex_app_server_request_model_selection,
)
from .command_formatters import format_codex_display_text
from .conversation_binding_data import (
    create_codex_conversation_binding_data,
    read_codex_conversation_binding_data,
    read_codex_conversation_binding_data_record,
    resolve_codex_default_workspace_dir,
)
from .conversation_control import track_codex_conversation_active_turn
from .conversation_turn_collector import create_codex_conversation_turn_collector
from .conversation_turn_input import build_codex_conversation_turn_input
from .node_cli_sessions import resume_codex_cli_session_on_node

DEFAULT_BOUND_TURN_TIMEOUT_MS = 20 * 60_000
DEFAULT_AGENT_ID = "main"
VALID_AGENT_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9_-]{0,63}$", re.IGNORECASE)
INVALID_AGENT_ID_CHARS_PATTERN = re.compile(r"[^a-z0-9_-]+", re.IGNORECASE)
LEADING_DASH_PATTERN = re.compile(r"^-+")
TRAILING_DASH_PATTERN = re.compile(r"-+$")
NATIVE_CONVERSATION_INTERACTIVE_APPROVALS_UNAVAILABLE = "OpenClaw native Codex conversation binding cannot route interactive approvals yet; use the Codex harness or explicit /acp spawn codex for that workflow."

CODEX_CONVERSATION_THREAD_DEVELOPER_INSTRUCTIONS = "This Codex thread is bound to an OpenClaw conversation. Answer normally; OpenClaw will deliver your final response back to the conversation."

_global_queues: dict = {}


async def start_codex_conversation_thread(params: dict) -> dict:
    workspace_dir = (params.get("workspaceDir") or "").strip() or resolve_codex_default_workspace_dir(params.get("pluginConfig"))
    agent_dir = (params.get("agentDir") or "").strip()
    agent_lookup = _build_agent_lookup({"agentDir": agent_dir, "config": params.get("config")})
    existing_binding = await read_codex_app_server_binding(params["sessionFile"], {**agent_lookup})
    auth_profile_id = resolve_codex_app_server_auth_profile_id_for_agent({
        "authProfileId": params.get("authProfileId") or (existing_binding or {}).get("authProfileId"),
        **agent_lookup,
    })
    thread_id = (params.get("threadId") or "").strip()
    binding_params = {
        "pluginConfig": params.get("pluginConfig"),
        "sessionFile": params["sessionFile"],
        "workspaceDir": workspace_dir,
        "model": params.get("model"),
        "modelProvider": params.get("modelProvider"),
        "authProfileId": auth_profile_id,
        "approvalPolicy": params.get("approvalPolicy"),
        "sandbox": params.get("sandbox"),
        "serviceTier": params.get("serviceTier"),
        "config": params.get("config"),
        "sessionKey": params.get("sessionKey"),
        "agentId": params.get("agentId"),
        **agent_lookup,
    }
    if thread_id:
        await _attach_existing_thread({**binding_params, "threadId": thread_id})
    else:
        await _create_thread(binding_params)
    return create_codex_conversation_binding_data({
        "sessionFile": params["sessionFile"],
        "workspaceDir": workspace_dir,
        **({"agentDir": agent_dir} if agent_dir else {}),
        "agentId": params.get("agentId"),
    })


async def handle_codex_conversation_inbound_claim(event: dict, ctx: dict, options: Optional[dict] = None):
    options = options or {}
    data = read_codex_conversation_binding_data(ctx.get("pluginBinding"))
    if not data:
        return None
    if event.get("commandAuthorized") is not True:
        return {"handled": True}
    prompt = ((event.get("bodyForAgent") or "").strip() if event.get("bodyForAgent") else "") or ((event.get("content") or "").strip() if event.get("content") else "") or ""
    if not prompt:
        return {"handled": True}
    session_key = event.get("sessionKey") or ctx.get("sessionKey")
    native_execution_block = (
        resolve_codex_native_sandbox_block({"config": options.get("config"), "sessionKey": session_key, "surface": "Codex CLI node conversation binding"})
        if data["kind"] == "codex-cli-node-session"
        else resolve_codex_native_execution_block({"config": options.get("config"), "sessionKey": session_key, "agentId": data.get("agentId"), "surface": "Codex app-server conversation binding"})
    )
    if native_execution_block:
        return {"handled": True, "reply": {"text": native_execution_block}}
    if data["kind"] == "codex-cli-node-session":
        resume = options.get("resumeCodexCliSessionOnNode")
        if not resume:
            return {"handled": True, "reply": {"text": "Codex CLI node binding is unavailable because Gateway node runtime is not attached."}}
        try:
            result = await _enqueue_bound_turn(f"{data['nodeId']}:{data['sessionId']}", lambda: _run_cli_node_turn(data, prompt, resume, options))
            return {"handled": True, "reply": result["reply"]}
        except Exception as error:
            return {"handled": True, "reply": {"text": f"Codex CLI node turn failed: {format_codex_display_text(format_error_message(error))}"}}
    try:
        result = await _enqueue_bound_turn(data["sessionFile"], lambda: _run_bound_turn_with_missing_thread_recovery({
            "data": data, "prompt": prompt, "event": event, "config": options.get("config"),
            "sessionKey": session_key, "pluginConfig": options.get("pluginConfig"), "timeoutMs": options.get("timeoutMs"),
        }))
        return {"handled": True, "reply": result["reply"]}
    except Exception as error:
        return {"handled": True, "reply": {"text": f"Codex app-server turn failed: {format_codex_display_text(format_error_message(error))}"}}


async def handle_codex_conversation_binding_resolved(event: dict) -> None:
    if event.get("status") != "denied":
        return
    data = read_codex_conversation_binding_data_record(event.get("request", {}).get("data") or {})
    if not data or data["kind"] != "codex-app-server-session":
        return
    await clear_codex_app_server_binding(data["sessionFile"])


async def _run_cli_node_turn(data: dict, prompt: str, resume, options: dict) -> dict:
    resumed = await resume({"nodeId": data["nodeId"], "sessionId": data["sessionId"], "prompt": prompt, "cwd": data.get("cwd"), "timeoutMs": options.get("timeoutMs")})
    return {"reply": {"text": resumed["text"].strip() or "Codex completed without a text reply."}}


async def _resolve_thread_binding_runtime(params: dict) -> dict:
    agent_lookup = _build_agent_lookup({"agentDir": params.get("agentDir"), "config": params.get("config")})
    model_provider = _resolve_thread_request_model_provider({"authProfileId": params.get("authProfileId"), "modelProvider": params.get("modelProvider"), **agent_lookup})
    model_selection = _resolve_optional_thread_request_model_selection({"model": params.get("model"), "modelProvider": model_provider, "authProfileId": params.get("authProfileId"), **agent_lookup})
    reviewer_model_provider = _resolve_model_backed_reviewer_policy_provider({"authProfileId": params.get("authProfileId"), "modelProvider": params.get("modelProvider"), **agent_lookup})
    exec_policy, runtime = await _resolve_conversation_app_server_runtime({
        "pluginConfig": params.get("pluginConfig"), "config": params.get("config"), "agentId": params.get("agentId"),
        "sessionKey": params.get("sessionKey"), "workspaceDir": params["workspaceDir"],
        "modelProvider": reviewer_model_provider, "model": params.get("model"), "agentDir": params.get("agentDir"),
    })
    model_scoped_runtime = resolve_codex_app_server_for_model_provider({"appServer": runtime, "provider": reviewer_model_provider, "model": params.get("model"), "config": params.get("config"), "env": os.environ, "agentDir": params.get("agentDir")})
    _assert_native_conversation_approval_policy_supported({
        "execPolicy": exec_policy,
        "approvalPolicy": model_scoped_runtime["approvalPolicy"] if exec_policy.get("touched") else (params.get("approvalPolicy") or model_scoped_runtime["approvalPolicy"]),
        "approvalsReviewer": model_scoped_runtime["approvalsReviewer"],
        "modelBackedApprovalsReviewerUnavailable": not can_use_codex_model_backed_approvals_reviewer_for_model({"modelProvider": reviewer_model_provider, "model": params.get("model"), "config": params.get("config"), "env": os.environ, "agentDir": params.get("agentDir")}),
    })
    client = await get_leased_shared_codex_app_server_client({"startOptions": runtime["start"], "timeoutMs": runtime["requestTimeoutMs"], "authProfileId": params.get("authProfileId"), **agent_lookup})
    return {"execPolicy": exec_policy, "runtime": model_scoped_runtime, "agentLookup": agent_lookup, "model": model_selection.get("model") if model_selection else None, "modelProvider": (model_selection.get("modelProvider") if model_selection else None) or model_provider, "client": client}


def _build_thread_request_runtime_options(params: dict, resolved: dict) -> dict:
    service_tier = params.get("serviceTier") or resolved["runtime"].get("serviceTier")
    sandbox = resolved["runtime"]["sandbox"] if resolved["execPolicy"].get("touched") else (params.get("sandbox") or resolved["runtime"]["sandbox"])
    options = {
        "approvalPolicy": resolved["runtime"]["approvalPolicy"] if resolved["execPolicy"].get("touched") else (params.get("approvalPolicy") or resolved["runtime"]["approvalPolicy"]),
        "approvalsReviewer": resolved["runtime"]["approvalsReviewer"],
        **_codex_conversation_sandbox_or_permissions(resolved["runtime"], sandbox),
    }
    if service_tier:
        options["serviceTier"] = service_tier
    return options


def _codex_conversation_sandbox_or_permissions(runtime: dict, sandbox) -> dict:
    network_proxy = runtime.get("networkProxy")
    if network_proxy:
        return {"config": network_proxy["configPatch"]}
    return {"sandbox": sandbox}


async def _request_new_conversation_binding_thread(params: dict, resolved: dict):
    request_options = {"cwd": params["workspaceDir"]}
    if resolved.get("model"):
        request_options["model"] = resolved["model"]
    if resolved.get("modelProvider"):
        request_options["modelProvider"] = resolved["modelProvider"]
    request_options["personality"] = CODEX_NATIVE_PERSONALITY_NONE
    request_options.update(_build_thread_request_runtime_options(params, resolved))
    request_options["developerInstructions"] = CODEX_CONVERSATION_THREAD_DEVELOPER_INSTRUCTIONS
    request_options["experimentalRawEvents"] = True
    request_options["persistExtendedHistory"] = True
    return await resolved["client"].request("thread/start", request_options, {"timeoutMs": resolved["runtime"]["requestTimeoutMs"]})


async def _write_thread_binding_from_response(params: dict, resolved: dict, response) -> None:
    runtime_approval_policy = resolved["runtime"].get("approvalPolicy") if isinstance(resolved["runtime"].get("approvalPolicy"), str) else None
    await write_codex_app_server_binding(params["sessionFile"], {
        "threadId": response["thread"]["id"],
        "cwd": response["thread"].get("cwd") or params["workspaceDir"],
        "authProfileId": params.get("authProfileId"),
        "model": response.get("model") or resolved.get("model") or params.get("model"),
        "modelProvider": normalize_codex_app_server_binding_model_provider({"authProfileId": params.get("authProfileId"), "modelProvider": response.get("modelProvider") or resolved.get("modelProvider") or params.get("modelProvider"), **resolved["agentLookup"]}),
        "approvalPolicy": runtime_approval_policy if resolved["execPolicy"].get("touched") else (params.get("approvalPolicy") or runtime_approval_policy),
        "sandbox": resolved["runtime"]["sandbox"] if resolved["execPolicy"].get("touched") else (params.get("sandbox") or resolved["runtime"]["sandbox"]),
        "serviceTier": params.get("serviceTier") or resolved["runtime"].get("serviceTier"),
        "networkProxyProfileName": (resolved["runtime"].get("networkProxy") or {}).get("profileName"),
        "networkProxyConfigFingerprint": (resolved["runtime"].get("networkProxy") or {}).get("configFingerprint"),
    }, {**resolved["agentLookup"]})


async def _attach_existing_thread(params: dict) -> None:
    resolved = await _resolve_thread_binding_runtime(params)
    try:
        if resolved["runtime"].get("networkProxy"):
            response = await _request_new_conversation_binding_thread(params, resolved)
        else:
            request_options = {"threadId": params["threadId"]}
            if resolved.get("model"):
                request_options["model"] = resolved["model"]
            if resolved.get("modelProvider"):
                request_options["modelProvider"] = resolved["modelProvider"]
            request_options["personality"] = CODEX_NATIVE_PERSONALITY_NONE
            request_options.update(_build_thread_request_runtime_options(params, resolved))
            request_options["persistExtendedHistory"] = True
            response = await resolved["client"].request(CODEX_CONTROL_METHODS["resumeThread"], request_options, {"timeoutMs": resolved["runtime"]["requestTimeoutMs"]})
        await _write_thread_binding_from_response(params, resolved, response)
    finally:
        release_leased_shared_codex_app_server_client(resolved["client"])


async def _create_thread(params: dict) -> None:
    resolved = await _resolve_thread_binding_runtime(params)
    try:
        response = await _request_new_conversation_binding_thread(params, resolved)
        await _write_thread_binding_from_response(params, resolved, response)
    finally:
        release_leased_shared_codex_app_server_client(resolved["client"])


async def _resolve_conversation_app_server_runtime(params: dict) -> tuple:
    exec_policy = _resolve_conversation_exec_policy({"config": params.get("config"), "agentId": params.get("agentId"), "sessionKey": params.get("sessionKey")})
    sandbox_for_policy = None
    if exec_policy.get("touched") and exec_policy.get("security") == "full" and exec_policy.get("ask") != "off":
        sandbox_for_policy = await resolve_sandbox_context({"config": params.get("config"), "sessionKey": params.get("sessionKey"), "workspaceDir": params["workspaceDir"]})
    runtime = resolve_codex_app_server_runtime_options({
        "pluginConfig": params.get("pluginConfig"), "execPolicy": exec_policy, "modelProvider": params.get("modelProvider"),
        "model": params.get("model"), "config": params.get("config"), "agentDir": params.get("agentDir"),
        "openClawSandboxActive": bool((sandbox_for_policy or {}).get("enabled")),
    })
    return exec_policy, runtime


async def _run_bound_turn(params: dict) -> dict:
    agent_lookup = _build_agent_lookup({"agentDir": params["data"].get("agentDir"), "config": params.get("config")})
    binding = await read_codex_app_server_binding(params["data"]["sessionFile"], agent_lookup)
    if not binding or not binding.get("threadId"):
        raise Error("bound Codex conversation has no thread binding")
    thread_id = binding["threadId"]
    workspace_dir = binding.get("cwd") or params["data"]["workspaceDir"]
    reviewer_model_provider = _resolve_model_backed_reviewer_policy_provider({"authProfileId": binding.get("authProfileId"), "modelProvider": binding.get("modelProvider"), **agent_lookup})
    exec_policy, runtime = await _resolve_conversation_app_server_runtime({
        "pluginConfig": params.get("pluginConfig"), "config": params.get("config"), "agentId": params["data"].get("agentId"),
        "sessionKey": params.get("sessionKey"), "workspaceDir": workspace_dir, "modelProvider": reviewer_model_provider,
        "model": binding.get("model"), "agentDir": params["data"].get("agentDir"),
    })
    model_scoped_runtime = resolve_codex_app_server_for_model_provider({"appServer": runtime, "provider": reviewer_model_provider, "model": binding.get("model"), "config": params.get("config"), "env": os.environ, "agentDir": params["data"].get("agentDir")})
    model_backed_approvals_reviewer_unavailable = not can_use_codex_model_backed_approvals_reviewer_for_model({"modelProvider": reviewer_model_provider, "model": binding.get("model"), "config": params.get("config"), "env": os.environ, "agentDir": params["data"].get("agentDir")})
    use_model_scoped_policy = exec_policy.get("touched") is True or model_backed_approvals_reviewer_unavailable
    approval_policy = model_scoped_runtime["approvalPolicy"] if use_model_scoped_policy else (binding.get("approvalPolicy") or model_scoped_runtime["approvalPolicy"])
    sandbox = model_scoped_runtime["sandbox"] if use_model_scoped_policy else (binding.get("sandbox") or model_scoped_runtime["sandbox"])
    service_tier = binding.get("serviceTier") or runtime.get("serviceTier")
    _assert_native_conversation_approval_policy_supported({"execPolicy": exec_policy, "approvalPolicy": approval_policy, "approvalsReviewer": model_scoped_runtime["approvalsReviewer"], "modelBackedApprovalsReviewerUnavailable": model_backed_approvals_reviewer_unavailable})
    model_selection = resolve_codex_app_server_request_model_selection({"model": binding["model"], "modelProvider": binding.get("modelProvider"), "authProfileId": binding.get("authProfileId"), **agent_lookup}) if binding.get("model") else None
    client = await get_leased_shared_codex_app_server_client({"startOptions": runtime["start"], "timeoutMs": runtime["requestTimeoutMs"], "authProfileId": binding.get("authProfileId"), **agent_lookup})
    try:
        collector = create_codex_conversation_turn_collector(thread_id)
        notification_cleanup = client.add_notification_handler(lambda notification: collector.handle_notification(notification))

        async def _request_handler(request):
            method = request.get("method", "")
            if method == "item/tool/call":
                return {"contentItems": [{"type": "inputText", "text": "OpenClaw native Codex conversation binding does not expose dynamic OpenClaw tools yet."}], "success": False}
            if method in ("item/commandExecution/requestApproval", "item/fileChange/requestApproval"):
                return {"decision": "decline", "reason": NATIVE_CONVERSATION_INTERACTIVE_APPROVALS_UNAVAILABLE}
            if method == "item/permissions/requestApproval":
                return {"permissions": {}, "scope": "turn"}
            if "requestApproval" in method:
                return {"decision": "decline", "reason": NATIVE_CONVERSATION_INTERACTIVE_APPROVALS_UNAVAILABLE}
            return None

        request_cleanup = client.add_request_handler(_request_handler)
        turn_request = {"threadId": thread_id, "input": build_codex_conversation_turn_input({"prompt": params["prompt"], "event": params["event"]}), "cwd": workspace_dir, "approvalPolicy": approval_policy, "approvalsReviewer": model_scoped_runtime["approvalsReviewer"], "personality": CODEX_NATIVE_PERSONALITY_NONE}
        if model_selection and model_selection.get("model"):
            turn_request["model"] = model_selection["model"]
        if service_tier:
            turn_request["serviceTier"] = service_tier
        turn_request["sandboxPolicy"] = codex_sandbox_policy_for_turn(sandbox, workspace_dir)
        response = await client.request("turn/start", turn_request, {"timeoutMs": runtime["requestTimeoutMs"]})
        turn_id = response["turn"]["id"]
        active_cleanup = await track_codex_conversation_active_turn({"sessionFile": params["data"]["sessionFile"], "threadId": thread_id, "turnId": turn_id})
        collector.set_turn_id(turn_id)
        try:
            completion = await collector.wait({"timeoutMs": params.get("timeoutMs") or DEFAULT_BOUND_TURN_TIMEOUT_MS})
        finally:
            active_cleanup()
        reply_text = completion["replyText"].strip()
        return {"reply": {"text": reply_text or "Codex completed without a text reply."}}
    finally:
        notification_cleanup()
        request_cleanup()
        release_leased_shared_codex_app_server_client(client)


async def _run_bound_turn_with_missing_thread_recovery(params: dict) -> dict:
    try:
        return await _run_bound_turn(params)
    except Exception as error:
        if not _is_codex_thread_not_found_error(error):
            raise
        agent_lookup = _build_agent_lookup({"agentDir": params["data"].get("agentDir"), "config": params.get("config")})
        binding = await read_codex_app_server_binding(params["data"]["sessionFile"], agent_lookup)
        exec_policy = _resolve_conversation_exec_policy({"config": params.get("config"), "agentId": params["data"].get("agentId"), "sessionKey": params.get("sessionKey")})
        use_current_runtime_policy = exec_policy.get("touched")
        await start_codex_conversation_thread({
            "pluginConfig": params.get("pluginConfig"), "sessionFile": params["data"]["sessionFile"],
            "workspaceDir": (binding or {}).get("cwd") or params["data"]["workspaceDir"],
            "model": (binding or {}).get("model"), "modelProvider": (binding or {}).get("modelProvider"),
            "authProfileId": (binding or {}).get("authProfileId"),
            "approvalPolicy": None if use_current_runtime_policy else (binding or {}).get("approvalPolicy"),
            "sandbox": None if use_current_runtime_policy else (binding or {}).get("sandbox"),
            "serviceTier": (binding or {}).get("serviceTier"), "config": params.get("config"),
            "sessionKey": params.get("sessionKey"), "agentId": params["data"].get("agentId"),
            **agent_lookup,
        })
        return await _run_bound_turn(params)


def _assert_native_conversation_approval_policy_supported(params: dict) -> None:
    if params["approvalPolicy"] != "never" and (params["execPolicy"].get("touched") is True or (params["modelBackedApprovalsReviewerUnavailable"] and params["approvalsReviewer"] == "user")):
        raise Error(NATIVE_CONVERSATION_INTERACTIVE_APPROVALS_UNAVAILABLE)


def _resolve_conversation_exec_policy(params: dict) -> dict:
    agent_id = params.get("agentId")
    if not agent_id and params.get("config"):
        agent_id = resolve_session_agent_ids({"sessionKey": params.get("sessionKey"), "config": params["config"]})["sessionAgentId"]
    return resolve_open_claw_exec_policy_for_codex_app_server({
        "config": params.get("config"), "agentId": agent_id,
        "execOverrides": _read_session_exec_overrides({"config": params.get("config"), "agentId": agent_id, "sessionKey": params.get("sessionKey")}),
        "approvals": load_exec_approvals(),
    })


def _read_session_exec_overrides(params: dict):
    session_key = (params.get("sessionKey") or "").strip()
    if not params.get("config") or not session_key:
        return None
    if not _can_read_session_exec_overrides({"config": params["config"], "agentId": params.get("agentId"), "sessionKey": session_key}):
        return None
    store_path = resolve_store_path(params["config"].get("session", {}).get("store"), {"agentId": params.get("agentId")})
    entry = get_session_entry({"storePath": store_path, "sessionKey": session_key, "readConsistency": "latest"})
    if not entry or (not entry.get("execSecurity") and not entry.get("execAsk")):
        return None
    return {"security": entry.get("execSecurity"), "ask": entry.get("execAsk")}


def _can_read_session_exec_overrides(params: dict) -> bool:
    agent_id = _normalize_agent_id_or_default(params.get("agentId"))
    if not agent_id:
        return True
    session_agent_id = _parse_agent_id_from_session_key(params.get("sessionKey"))
    if not session_agent_id:
        return _is_default_agent_session_key_for_agent({"config": params["config"], "agentId": agent_id})
    return session_agent_id == agent_id


def _parse_agent_id_from_session_key(session_key: Optional[str]) -> Optional[str]:
    raw = (session_key or "").strip()
    if not raw:
        return None
    parts = [p for p in raw.lower().split(":") if p]
    if len(parts) < 3 or parts[0] != "agent" or not parts[2]:
        return None
    return _normalize_agent_id_or_default(parts[1])


def _is_default_agent_session_key_for_agent(params: dict) -> bool:
    return _normalize_agent_id(params["agentId"]) == _resolve_default_policy_agent_id(params["config"])


def _resolve_default_policy_agent_id(config) -> str:
    agents = [entry for entry in ((config.get("agents") or {}).get("list") or []) if isinstance(entry, dict)]
    default_entry = next((entry for entry in agents if entry.get("default")), agents[0] if agents else None)
    return _normalize_agent_id(default_entry.get("id") if default_entry else None)


def _normalize_agent_id_or_default(value=None) -> Optional[str]:
    normalized = _normalize_agent_id(value)
    if normalized == DEFAULT_AGENT_ID and not (value or "").strip():
        return None
    return normalized


def _normalize_agent_id(value=None) -> str:
    trimmed = (value or "").strip()
    if not trimmed:
        return DEFAULT_AGENT_ID
    normalized = trimmed.lower()
    if VALID_AGENT_ID_PATTERN.match(trimmed):
        return normalized
    result = TRAILING_DASH_PATTERN.sub("", LEADING_DASH_PATTERN.sub("", INVALID_AGENT_ID_CHARS_PATTERN.sub("-", normalized)))[:64]
    return result or DEFAULT_AGENT_ID


def _is_codex_thread_not_found_error(error) -> bool:
    message = format_error_message(error)
    return bool(re.search(r"\bthread not found:", message, re.IGNORECASE) or re.search(r"\bbound Codex conversation has no thread binding\b", message))


async def _enqueue_bound_turn(key: str, run):
    previous = _global_queues.get(key)
    if previous is None:
        previous = asyncio.Future()
        previous.set_result(None)
    next_future = asyncio.ensure_future(_run_after(previous, run))

    async def _cleanup():
        try:
            await next_future
        except Exception:
            pass
        if _global_queues.get(key) is queued:
            _global_queues.pop(key, None)

    queued = asyncio.ensure_future(_cleanup())
    _global_queues[key] = queued
    return await next_future


async def _run_after(previous, run):
    try:
        await previous
    except Exception:
        pass
    return await run()


def _resolve_thread_request_model_provider(params: dict) -> Optional[str]:
    model_provider = (params.get("modelProvider") or "").strip()
    if not model_provider or model_provider.lower() == "codex":
        return None
    if _is_codex_app_server_native_auth_profile(params) and model_provider.lower() == "openai":
        return None
    return "openai" if model_provider.lower() == "openai" else model_provider


def _resolve_optional_thread_request_model_selection(params: dict):
    if not (params.get("model") or "").strip():
        return None
    return resolve_codex_app_server_request_model_selection({"model": params["model"], "modelProvider": params.get("modelProvider"), "authProfileId": params.get("authProfileId"), "agentDir": params.get("agentDir"), "config": params.get("config")})


def _resolve_model_backed_reviewer_policy_provider(params: dict) -> Optional[str]:
    model_provider = (params.get("modelProvider") or "").strip()
    if model_provider and model_provider.lower() != "codex":
        return "openai" if model_provider.lower() == "openai" else model_provider
    return "openai" if _is_codex_app_server_native_auth_profile(params) else None


def _build_agent_lookup(params: dict) -> dict:
    agent_dir = (params.get("agentDir") or "").strip()
    lookup = {}
    if agent_dir:
        lookup["agentDir"] = agent_dir
    if params.get("config"):
        lookup["config"] = params["config"]
    return lookup


class Error(Exception):
    pass
