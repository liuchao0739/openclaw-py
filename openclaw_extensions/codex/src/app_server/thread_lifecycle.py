"""Codex app-server thread lifecycle prompt builders."""

from __future__ import annotations

from typing import Any

CODEX_NATIVE_PERSONALITY_NONE = "none"


def _join_present_sections(*sections: Any) -> str:
    return "\n\n".join(
        section.strip()
        for section in sections
        if isinstance(section, str) and section.strip()
    )


def _flatten_dynamic_tool_functions(dynamic_tools: list[dict[str, Any]] | None) -> list[dict[str, Any]]:
    if not dynamic_tools:
        return []
    flattened: list[dict[str, Any]] = []
    for tool in dynamic_tools:
        if tool.get("type") == "namespace":
            namespace = str(tool.get("name") or "").strip()
            for child in tool.get("tools") or []:
                if isinstance(child, dict):
                    flattened.append({**child, "namespace": namespace})
        elif isinstance(tool, dict):
            flattened.append(tool)
    return flattened


def _build_deferred_dynamic_tool_manifest(dynamic_tools: list[dict[str, Any]] | None) -> str | None:
    deferred = sorted(
        {
            str(tool.get("name") or "").strip()
            for tool in _flatten_dynamic_tool_functions(dynamic_tools)
            if tool.get("deferLoading") is True and str(tool.get("name") or "").strip()
        }
    )
    if not deferred:
        return None
    return (
        "Deferred searchable OpenClaw dynamic tools available: "
        f"{', '.join(deferred)}. Use `tool_search` to load exact callable specs before use."
    )


def _build_visible_reply_instruction(params: dict[str, Any], dynamic_tools: list[dict[str, Any]] | None) -> str:
    message_tool_available = (
        any(str(tool.get("name") or "").strip() == "message" for tool in _flatten_dynamic_tool_functions(dynamic_tools))
        if dynamic_tools
        else params.get("disableMessageTool") is not True
    )
    if params.get("sourceReplyDeliveryMode") == "message_tool_only" and message_tool_available:
        return (
            "Visible source replies are not automatically delivered for this run. "
            "Use `message(action=send)` for user-visible source-channel output. "
            "Do not repeat that visible content in your final answer."
        )
    if message_tool_available:
        return (
            "For the current source conversation, reply normally in your final assistant message; "
            "OpenClaw will deliver it through the active source conversation. Use `message` only "
            "for explicit out-of-band sends, media/file sends, or sends to a different target."
        )
    return (
        "For the current source conversation, reply normally in your final assistant message; "
        "OpenClaw will deliver it through the active source conversation."
    )


def build_developer_instructions(
    params: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> str:
    options = options or {}
    dynamic_tools = options.get("dynamicTools")
    sections = [
        (
            "You are a personal agent running inside OpenClaw. OpenClaw has dynamic tools for "
            "OpenClaw-owned messaging, cron, sessions, media, gateway, and nodes."
        ),
        _build_deferred_dynamic_tool_manifest(dynamic_tools if isinstance(dynamic_tools, list) else None),
        (
            "Use Codex native `spawn_agent` for Codex subagents. Use OpenClaw `sessions_spawn` "
            "only for OpenClaw or ACP delegation."
        ),
        _build_visible_reply_instruction(params, dynamic_tools if isinstance(dynamic_tools, list) else None),
        params.get("extraSystemPrompt"),
    ]
    return _join_present_sections(*sections)


def _resolve_codex_app_server_model_provider(params: dict[str, Any]) -> str | None:
    provider = str(params.get("provider") or "").strip()
    provider_lower = provider.lower()
    if not provider or provider_lower == "codex":
        return None
    return "openai" if provider_lower == "openai" else provider


def _resolve_codex_app_server_request_model_selection(params: dict[str, Any]) -> dict[str, Any]:
    model = str(params.get("model") or params.get("modelId") or "").strip()
    model_provider = params.get("modelProvider")
    if model_provider is None:
        model_provider = _resolve_codex_app_server_model_provider(params)
    result: dict[str, Any] = {"model": model}
    if model_provider:
        result["modelProvider"] = model_provider
    return result


def _to_codex_legacy_dynamic_tool(tool: dict[str, Any], namespace: str | None = None) -> dict[str, Any]:
    legacy = {key: value for key, value in tool.items() if key != "type"}
    if namespace:
        legacy["namespace"] = namespace
    return legacy


def _to_codex_thread_start_dynamic_tools(dynamic_tools: list[dict[str, Any]]) -> list[dict[str, Any]]:
    specs: list[dict[str, Any]] = []
    for tool in dynamic_tools:
        if tool.get("type") == "namespace":
            namespace = str(tool.get("name") or "").strip()
            for child in tool.get("tools") or []:
                if isinstance(child, dict):
                    specs.append(_to_codex_legacy_dynamic_tool(child, namespace))
        else:
            specs.append(_to_codex_legacy_dynamic_tool(tool))
    return specs


def _build_codex_runtime_thread_config_for_run(
    _params: dict[str, Any],
    config: dict[str, Any] | None,
    _options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return dict(config or {})


def _codex_thread_sandbox_or_permissions(app_server: dict[str, Any]) -> dict[str, Any]:
    if app_server.get("networkProxy"):
        return {}
    return {"sandbox": app_server.get("sandbox")}


def build_thread_start_params(
    params: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    model_selection = _resolve_codex_app_server_request_model_selection(
        {
            **params,
            "model": options.get("model") or params.get("modelId"),
            "modelProvider": options.get("modelProvider")
            or _resolve_codex_app_server_model_provider(params),
        }
    )
    developer_instructions = options.get("developerInstructions") or build_developer_instructions(
        params,
        {"dynamicTools": options.get("dynamicTools")},
    )
    result: dict[str, Any] = {
        "model": model_selection["model"],
        "cwd": options["cwd"],
        "approvalPolicy": options["appServer"]["approvalPolicy"],
        "approvalsReviewer": options["appServer"]["approvalsReviewer"],
        "personality": CODEX_NATIVE_PERSONALITY_NONE,
        "serviceName": "OpenClaw",
        "config": _build_codex_runtime_thread_config_for_run(params, options.get("config"), options),
        "developerInstructions": developer_instructions,
        "dynamicTools": _to_codex_thread_start_dynamic_tools(options.get("dynamicTools") or []),
        "experimentalRawEvents": True,
        "persistExtendedHistory": True,
    }
    if model_selection.get("modelProvider"):
        result["modelProvider"] = model_selection["modelProvider"]
    result.update(_codex_thread_sandbox_or_permissions(options["appServer"]))
    if options["appServer"].get("serviceTier") is not None:
        result["serviceTier"] = options["appServer"]["serviceTier"]
    return result


def build_thread_resume_params(
    params: dict[str, Any],
    options: dict[str, Any],
) -> dict[str, Any]:
    model_selection = _resolve_codex_app_server_request_model_selection(
        {
            **params,
            "model": options.get("model") or params.get("modelId"),
            "modelProvider": options.get("modelProvider")
            or _resolve_codex_app_server_model_provider(
                {
                    **params,
                    "authProfileId": options.get("authProfileId") or params.get("authProfileId"),
                }
            ),
        }
    )
    developer_instructions = options.get("developerInstructions") or build_developer_instructions(
        params,
        {"dynamicTools": options.get("dynamicTools")},
    )
    result: dict[str, Any] = {
        "threadId": options["threadId"],
        "model": model_selection["model"],
        "approvalPolicy": options["appServer"]["approvalPolicy"],
        "approvalsReviewer": options["appServer"]["approvalsReviewer"],
        "personality": CODEX_NATIVE_PERSONALITY_NONE,
        "config": _build_codex_runtime_thread_config_for_run(params, options.get("config"), options),
        "developerInstructions": developer_instructions,
        "persistExtendedHistory": True,
    }
    if model_selection.get("modelProvider"):
        result["modelProvider"] = model_selection["modelProvider"]
    result.update(_codex_thread_sandbox_or_permissions(options["appServer"]))
    if options["appServer"].get("serviceTier") is not None:
        result["serviceTier"] = options["appServer"]["serviceTier"]
    return result


def _build_user_input(params: dict[str, Any], prompt_text: str | None = None) -> list[dict[str, Any]]:
    prompt = prompt_text if prompt_text is not None else str(params.get("prompt") or "")
    inputs: list[dict[str, Any]] = [{"type": "text", "text": prompt, "text_elements": []}]
    for image in params.get("images") or []:
        if not isinstance(image, dict):
            continue
        mime_type = image.get("mimeType") or "image/png"
        data = image.get("data") or ""
        inputs.append({"type": "image", "url": f"data:{mime_type};base64,{data}"})
    return inputs


def resolve_reasoning_effort(think_level: str | None, model_id: str | None) -> str | None:
    from openclaw_extensions.codex.provider import is_modern_codex_model

    level = str(think_level or "").strip().lower()
    model = str(model_id or "").strip().lower()
    if level == "minimal" and is_modern_codex_model(model):
        return "low"
    return level or None


def build_turn_collaboration_mode(params: dict[str, Any], options: dict[str, Any] | None = None) -> dict[str, Any]:
    options = options or {}
    model = options.get("model") or params.get("modelId")
    developer_instructions = _join_present_sections(
        options.get("turnScopedDeveloperInstructions"),
        options.get("memoryCollaborationInstructions"),
        options.get("skillsCollaborationInstructions"),
        options.get("heartbeatCollaborationInstructions"),
    ) or None
    return {
        "mode": "default",
        "settings": {
            "model": model,
            "reasoning_effort": resolve_reasoning_effort(params.get("thinkLevel"), model),
            "developer_instructions": developer_instructions,
        },
    }


def build_turn_start_params(params: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    model_selection = _resolve_codex_app_server_request_model_selection(
        {
            **params,
            "model": options.get("model") or params.get("modelId"),
            "modelProvider": options.get("modelProvider"),
        }
    )
    app_server = options["appServer"]
    use_thread_permission_profile = bool(app_server.get("networkProxy")) and not options.get("sandboxPolicy")
    result: dict[str, Any] = {
        "threadId": options["threadId"],
        "input": _build_user_input(params, options.get("promptText")),
        "cwd": options["cwd"],
        "approvalPolicy": app_server["approvalPolicy"],
        "approvalsReviewer": app_server["approvalsReviewer"],
        "model": model_selection["model"],
        "personality": CODEX_NATIVE_PERSONALITY_NONE,
        "effort": resolve_reasoning_effort(params.get("thinkLevel"), model_selection["model"]),
        "collaborationMode": build_turn_collaboration_mode(
            params,
            {
                "model": model_selection["model"],
                "turnScopedDeveloperInstructions": options.get("turnScopedDeveloperInstructions"),
                "skillsCollaborationInstructions": options.get("skillsCollaborationInstructions"),
                "memoryCollaborationInstructions": options.get("memoryCollaborationInstructions"),
                "heartbeatCollaborationInstructions": options.get("heartbeatCollaborationInstructions"),
            },
        ),
    }
    if not use_thread_permission_profile:
        result["sandboxPolicy"] = options.get("sandboxPolicy") or app_server.get("sandbox")
    if app_server.get("serviceTier") is not None:
        result["serviceTier"] = app_server["serviceTier"]
    if options.get("environmentSelection"):
        result["environments"] = options["environmentSelection"]
    return result
