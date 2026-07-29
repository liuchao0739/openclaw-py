import uuid
from typing import Any, Optional

from .._sdk import read_string_param, read_string_value, read_positive_integer_param, json_result
from .browser_tool_schema import (
    BrowserToolSchema,
    _BROWSER_ACT_REQUEST_KEYS,
    _LEGACY_BROWSER_ACT_SHARED_REQUEST_KEYS,
)

DEFAULT_BROWSER_SCREENSHOT_TIMEOUT_MS = 15000
DEFAULT_BROWSER_PROXY_TIMEOUT_MS = 20000
BROWSER_PROXY_GATEWAY_TIMEOUT_SLACK_MS = 5000
DEFAULT_EXISTING_SESSION_MANAGE_TIMEOUT_MS = 45000

_EXISTING_SESSION_MANAGE_ACTIONS = {
    "status", "start", "stop", "profiles", "tabs", "open", "focus", "close",
}

_EAGER_BROWSER_CONTROL_SERVICE_ENV = "OPENCLAW_EAGER_BROWSER_CONTROL_SERVER"


def _normalize_optional_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed or None
    return None


def _is_truthy_env_value(value: Optional[str]) -> bool:
    if not value:
        return False
    return value.strip().lower() in ("1", "true", "yes", "on")


def _derive_chat_type_from_session_key(session_key: Optional[str]) -> Optional[str]:
    if not session_key:
        return None
    tokens = {t for t in session_key.lower().split(":") if t}
    if "group" in tokens:
        return "group"
    if "channel" in tokens:
        return "channel"
    if "direct" in tokens or "dm" in tokens:
        return "direct"
    return None


def _read_optional_target_and_timeout(params: dict) -> dict:
    target_id = _normalize_optional_string(params.get("targetId"))
    timeout_ms = read_positive_integer_param(
        params, "timeoutMs", message="timeoutMs must be a positive integer."
    )
    return {"targetId": target_id, "timeoutMs": timeout_ms}


def _read_target_url_param(params: dict) -> str:
    target_url = read_string_param(params, "targetUrl")
    if target_url:
        return target_url
    return read_string_param(params, "url", required=True)


def _read_act_request_param(params: dict) -> Optional[dict]:
    request_param = params.get("request")
    if request_param and isinstance(request_param, dict):
        request = dict(request_param)
        has_mismatched_kind = (
            isinstance(request.get("kind"), str)
            and isinstance(params.get("kind"), str)
            and request["kind"] != params["kind"]
        )
        for key in _BROWSER_ACT_REQUEST_KEYS:
            if key in request or key not in params:
                continue
            if has_mismatched_kind and key not in _LEGACY_BROWSER_ACT_SHARED_REQUEST_KEYS:
                continue
            request[key] = params[key]
        return request

    kind = read_string_param(params, "kind")
    if not kind:
        return None

    request: dict = {}
    for key in _BROWSER_ACT_REQUEST_KEYS:
        if key not in params:
            continue
        request[key] = params[key]
    return request


def _is_browser_node(node: dict) -> bool:
    caps = node.get("caps", [])
    commands = node.get("commands", [])
    if not isinstance(caps, list):
        caps = []
    if not isinstance(commands, list):
        commands = []
    return "browser" in caps or "browser.proxy" in commands


async def _resolve_browser_node_target(params: dict, deps: dict) -> Optional[dict]:
    cfg = deps["getRuntimeConfig"]()
    policy = (cfg.get("gateway", {}) or {}).get("nodes", {}).get("browser", {})
    mode = policy.get("mode", "auto")
    if mode == "off":
        if params.get("target") == "node" or params.get("requestedNode"):
            raise RuntimeError("Node browser proxy is disabled (gateway.nodes.browser.mode=off).")
        return None
    sandbox_bridge_url = params.get("sandboxBridgeUrl", "") or ""
    if sandbox_bridge_url.strip() and params.get("target") != "node" and not params.get("requestedNode"):
        return None
    if params.get("target") and params.get("target") != "node":
        return None
    if mode == "manual" and params.get("target") != "node" and not params.get("requestedNode"):
        return None

    nodes = await deps["listNodes"]({})
    browser_nodes = [n for n in nodes if n.get("connected") and _is_browser_node(n)]
    if not browser_nodes:
        if params.get("target") == "node" or params.get("requestedNode"):
            raise RuntimeError("No connected browser-capable nodes.")
        return None

    requested = (params.get("requestedNode") or "").strip() or (policy.get("node") or "").strip()
    if requested:
        node_id = deps["resolveNodeIdFromList"](browser_nodes, requested, False)
        node = next((n for n in browser_nodes if n.get("nodeId") == node_id), None)
        return {"nodeId": node_id, "label": (node.get("displayName") or node.get("remoteIp") or node_id) if node else node_id}

    selected = deps["selectDefaultNodeFromList"](browser_nodes, preferLocalMac=False, fallback="none")

    if params.get("target") == "node":
        if selected:
            return {
                "nodeId": selected["nodeId"],
                "label": selected.get("displayName") or selected.get("remoteIp") or selected["nodeId"],
            }
        raise RuntimeError(
            f"Multiple browser-capable nodes connected ({len(browser_nodes)}). "
            "Set gateway.nodes.browser.node or pass node=<id>."
        )

    if mode == "manual":
        return None

    if selected:
        return {
            "nodeId": selected["nodeId"],
            "label": selected.get("displayName") or selected.get("remoteIp") or selected["nodeId"],
        }
    return None


async def _call_browser_proxy(params: dict, deps: dict) -> dict:
    timeout_ms = params.get("timeoutMs")
    if isinstance(timeout_ms, (int, float)) and timeout_ms == timeout_ms:
        proxy_timeout_ms = max(1, int(timeout_ms))
    else:
        proxy_timeout_ms = DEFAULT_BROWSER_PROXY_TIMEOUT_MS
    gateway_timeout_ms = proxy_timeout_ms + BROWSER_PROXY_GATEWAY_TIMEOUT_SLACK_MS
    payload = await deps["callGatewayTool"](
        "node.invoke",
        {"timeoutMs": gateway_timeout_ms},
        {
            "nodeId": params["nodeId"],
            "command": "browser.proxy",
            "params": {
                "method": params["method"],
                "path": params["path"],
                "query": params.get("query"),
                "body": params.get("body"),
                "timeoutMs": proxy_timeout_ms,
                "profile": params.get("profile"),
            },
            "idempotencyKey": str(uuid.uuid4()),
        },
    )
    parsed = _unwrap_browser_proxy_payload(payload)
    if not parsed or not isinstance(parsed, dict) or "result" not in parsed:
        raise RuntimeError("browser proxy failed")
    return parsed


def _unwrap_browser_proxy_payload(payload: Any) -> Any:
    if payload is None:
        return None
    if isinstance(payload, dict):
        if payload.get("payload") is not None:
            return payload["payload"]
        payload_json = payload.get("payloadJSON")
        if isinstance(payload_json, str) and payload_json.strip():
            import json
            try:
                return json.loads(payload_json)
            except Exception:
                return None
    return None


def _resolve_browser_base_url(params: dict, deps: dict) -> Optional[str]:
    cfg = deps["getRuntimeConfig"]()
    resolved = deps["resolveBrowserConfig"](cfg.get("browser", {}), cfg)
    normalized_sandbox = (params.get("sandboxBridgeUrl") or "").strip()
    target = params.get("target") or ("sandbox" if normalized_sandbox else "host")

    if target == "sandbox":
        if not normalized_sandbox:
            raise RuntimeError(
                'Sandbox browser is unavailable. Enable agents.defaults.sandbox.browser.enabled or use target="host" if allowed.'
            )
        return normalized_sandbox.rstrip("/")

    if params.get("allowHostControl") is False:
        raise RuntimeError("Host browser control is disabled by sandbox policy.")
    if not resolved.get("enabled"):
        raise RuntimeError(
            "Browser control is disabled. Set browser.enabled=true in ~/.openclaw/openclaw.json."
        )
    return None


def _should_prefer_host_for_profile(profile_name: Optional[str], deps: dict) -> bool:
    if not profile_name:
        return False
    cfg = deps["getRuntimeConfig"]()
    resolved = deps["resolveBrowserConfig"](cfg.get("browser", {}), cfg)
    profile = deps["resolveProfile"](resolved, profile_name)
    if not profile:
        return False
    capabilities = deps["getBrowserProfileCapabilities"](profile)
    return capabilities.get("usesChromeMcp", False)


def _uses_existing_session_manage_flow(params: dict, deps: dict) -> bool:
    if params["action"] not in _EXISTING_SESSION_MANAGE_ACTIONS:
        return False
    cfg = deps["getRuntimeConfig"]()
    resolved = deps["resolveBrowserConfig"](cfg.get("browser", {}), cfg)
    profile = deps["resolveProfile"](resolved, params.get("profileName") or resolved.get("defaultProfile"))
    if profile and deps["getBrowserProfileCapabilities"](profile).get("usesChromeMcp"):
        return True
    if params["action"] != "profiles":
        return False
    profiles = resolved.get("profiles", {})
    if not isinstance(profiles, dict):
        return False
    return any(
        (deps["getBrowserProfileCapabilities"](deps["resolveProfile"](resolved, name)) or {}).get("usesChromeMcp", False)
        for name in profiles
    )


def _read_tool_timeout_ms(params: dict) -> Optional[int]:
    return read_positive_integer_param(
        params, "timeoutMs", message="timeoutMs must be a positive integer."
    )


def create_browser_tool(opts: Optional[dict] = None, deps: Optional[dict] = None) -> dict:
    opts = opts or {}
    deps = deps or {}
    target_default = "sandbox" if opts.get("sandboxBridgeUrl") else "host"
    host_hint = "Host target blocked by policy." if opts.get("allowHostControl") is False else "Host target allowed."

    description = " ".join([
        "Control the browser via OpenClaw's browser control server (status/start/stop/profiles/tabs/open/snapshot/screenshot/actions).",
        "Browser choice: omit profile by default for the isolated OpenClaw-managed browser (`openclaw`).",
        'For the logged-in user browser, use profile="user". A supported Chromium-based browser (v144+) must be running on the selected host or browser node. Use only when existing logins/cookies matter and the user is present.',
        'For profile="user" or other existing-session profiles, omit timeoutMs on act:type, evaluate, hover, scrollIntoView, drag, select, and fill; that driver rejects per-call timeout overrides for those actions.',
        'When a node-hosted browser proxy is available, the tool may auto-route to it. Pin a node with node=<id|name> or target="node".',
        "When using refs from snapshot (e.g. e12), keep the same tab: prefer passing targetId from the snapshot response into subsequent actions (act/click/type/etc). For tab operations, targetId also accepts tabId handles (t1) and labels from action=tabs.",
        "For multi-step browser work, login checks, stale refs, duplicate tabs, or Google Meet flows, use the bundled browser-automation skill when it is available.",
        'For stable, self-resolving refs across calls, use snapshot with refs="aria" (Playwright aria-ref ids). Default refs="role" are role+name-based.',
        "Use snapshot+act for UI automation. Avoid act:wait by default; use only in exceptional cases when no reliable UI state exists.",
        f"target selects browser location (sandbox|host|node). Default: {target_default}.",
        host_hint,
    ])

    async def execute(_tool_call_id: str, args: dict, signal: Any = None, on_update: Any = None) -> dict:
        params = args
        action = read_string_param(params, "action", required=True)
        profile = read_string_param(params, "profile")
        requested_node = read_string_param(params, "node")
        requested_timeout_ms = _read_tool_timeout_ms(params)
        target = read_string_param(params, "target")
        configured_node = (deps["getRuntimeConfig"]().get("gateway", {}).get("nodes", {}).get("browser", {}).get("node") or "").strip()

        if requested_node and target and target != "node":
            raise RuntimeError('node is only supported with target="node".')
        is_user_browser_profile = _should_prefer_host_for_profile(profile, deps)
        if is_user_browser_profile and target == "sandbox":
            raise RuntimeError(
                f'profile="{profile}" cannot use the sandbox browser; use target="host" or omit target.'
            )

        node_target: Optional[dict] = None
        try:
            node_target = await _resolve_browser_node_target({
                "requestedNode": requested_node,
                "target": target,
                "sandboxBridgeUrl": opts.get("sandboxBridgeUrl"),
            }, deps)
        except Exception as error:
            if not (is_user_browser_profile and not target and not requested_node and not configured_node):
                raise error
        if is_user_browser_profile and not target and not requested_node and not node_target:
            target = "host"

        resolved_target = None if target == "node" else target
        base_url = None
        if not node_target:
            base_url = _resolve_browser_base_url({
                "target": resolved_target,
                "sandboxBridgeUrl": opts.get("sandboxBridgeUrl"),
                "allowHostControl": opts.get("allowHostControl"),
            }, deps)

        proxy_request = None
        if node_target:
            async def proxy_request(opts_local: dict):
                proxy = await _call_browser_proxy({
                    "nodeId": node_target["nodeId"],
                    "method": opts_local["method"],
                    "path": opts_local["path"],
                    "query": opts_local.get("query"),
                    "body": opts_local.get("body"),
                    "timeoutMs": opts_local.get("timeoutMs"),
                    "profile": opts_local.get("profile", profile),
                }, deps)
                mapping = await deps["persistBrowserProxyFiles"](proxy.get("files"))
                deps["applyBrowserProxyPaths"](proxy.get("result"), mapping)
                return proxy["result"]

        tool_timeout_ms = requested_timeout_ms
        if tool_timeout_ms is None and _uses_existing_session_manage_flow({
            "action": action,
            "profileName": profile,
        }, deps):
            tool_timeout_ms = DEFAULT_EXISTING_SESSION_MANAGE_TIMEOUT_MS

        def touch_tracked_tab(target_id: Optional[str]):
            if proxy_request or not target_id:
                return
            deps["touchSessionBrowserTab"]({
                "sessionKey": opts.get("agentSessionKey"),
                "targetId": target_id,
                "baseUrl": base_url,
                "profile": profile,
            })

        if action == "doctor":
            if proxy_request:
                return json_result(await proxy_request({"method": "GET", "path": "/doctor", "profile": profile}))
            return json_result(await deps["browserDoctor"](base_url, {"profile": profile}))

        if action == "status":
            if proxy_request:
                return json_result(await proxy_request({"method": "GET", "path": "/", "profile": profile, "timeoutMs": tool_timeout_ms}))
            return json_result(await deps["browserStatus"](base_url, {"profile": profile, "timeoutMs": tool_timeout_ms}))

        if action == "start":
            if proxy_request:
                await proxy_request({"method": "POST", "path": "/start", "profile": profile, "timeoutMs": tool_timeout_ms})
                return json_result(await proxy_request({"method": "GET", "path": "/", "profile": profile, "timeoutMs": tool_timeout_ms}))
            await deps["browserStart"](base_url, {"profile": profile, "timeoutMs": tool_timeout_ms})
            return json_result(await deps["browserStatus"](base_url, {"profile": profile, "timeoutMs": tool_timeout_ms}))

        if action == "stop":
            if proxy_request:
                await proxy_request({"method": "POST", "path": "/stop", "profile": profile, "timeoutMs": tool_timeout_ms})
                return json_result(await proxy_request({"method": "GET", "path": "/", "profile": profile, "timeoutMs": tool_timeout_ms}))
            await deps["browserStop"](base_url, {"profile": profile, "timeoutMs": tool_timeout_ms})
            return json_result(await deps["browserStatus"](base_url, {"profile": profile, "timeoutMs": tool_timeout_ms}))

        if action == "profiles":
            if proxy_request:
                result = await proxy_request({"method": "GET", "path": "/profiles", "timeoutMs": tool_timeout_ms})
                return json_result(result)
            return json_result({"profiles": await deps["browserProfiles"](base_url, {"timeoutMs": tool_timeout_ms})})

        if action == "tabs":
            return await deps["executeTabsAction"]({
                "baseUrl": base_url,
                "profile": profile,
                "timeoutMs": tool_timeout_ms,
                "proxyRequest": proxy_request,
            })

        if action == "open":
            target_url = _read_target_url_param(params)
            label = _normalize_optional_string(params.get("label"))
            if proxy_request:
                body = {"url": target_url}
                if label:
                    body["label"] = label
                result = await proxy_request({"method": "POST", "path": "/tabs/open", "profile": profile, "body": body, "timeoutMs": tool_timeout_ms})
                return json_result(result)
            opened = await deps["browserOpenTab"](base_url, target_url, {
                "profile": profile,
                "label": label,
                "timeoutMs": tool_timeout_ms,
            })
            deps["trackSessionBrowserTab"]({
                "sessionKey": opts.get("agentSessionKey"),
                "targetId": opened.get("targetId"),
                "baseUrl": base_url,
                "profile": profile,
            })
            return json_result(opened)

        if action == "focus":
            target_id = read_string_param(params, "targetId", required=True)
            if proxy_request:
                result = await proxy_request({"method": "POST", "path": "/tabs/focus", "profile": profile, "body": {"targetId": target_id}, "timeoutMs": tool_timeout_ms})
                return json_result(result)
            await deps["browserFocusTab"](base_url, target_id, {"profile": profile, "timeoutMs": tool_timeout_ms})
            touch_tracked_tab(target_id)
            return json_result({"ok": True})

        if action == "close":
            target_id = read_string_param(params, "targetId")
            if proxy_request:
                if target_id:
                    result = await proxy_request({"method": "DELETE", "path": f"/tabs/{target_id}", "profile": profile, "timeoutMs": tool_timeout_ms})
                else:
                    result = await proxy_request({"method": "POST", "path": "/act", "profile": profile, "body": {"kind": "close"}, "timeoutMs": tool_timeout_ms})
                return json_result(result)
            if target_id:
                await deps["browserCloseTab"](base_url, target_id, {"profile": profile, "timeoutMs": tool_timeout_ms})
                deps["untrackSessionBrowserTab"]({
                    "sessionKey": opts.get("agentSessionKey"),
                    "targetId": target_id,
                    "baseUrl": base_url,
                    "profile": profile,
                })
            else:
                await deps["browserAct"](base_url, {"kind": "close"}, {"profile": profile, "timeoutMs": tool_timeout_ms})
            return json_result({"ok": True})

        if action == "snapshot":
            return await deps["executeSnapshotAction"]({
                "input": params,
                "baseUrl": base_url,
                "profile": profile,
                "proxyRequest": proxy_request,
                "onTabActivity": touch_tracked_tab,
            })

        if action == "screenshot":
            target_id = read_string_param(params, "targetId")
            full_page = bool(params.get("fullPage"))
            ref = read_string_param(params, "ref")
            element = read_string_param(params, "element")
            labels = params.get("labels") if isinstance(params.get("labels"), bool) else None
            image_type = "jpeg" if params.get("type") == "jpeg" else "png"
            effective_timeout_ms = requested_timeout_ms or DEFAULT_BROWSER_SCREENSHOT_TIMEOUT_MS
            body = {
                "targetId": target_id,
                "fullPage": full_page,
                "ref": ref,
                "element": element,
                "type": image_type,
                "labels": labels,
                "timeoutMs": effective_timeout_ms,
            }
            if proxy_request:
                result = await proxy_request({"method": "POST", "path": "/screenshot", "profile": profile, "timeoutMs": effective_timeout_ms, "body": body})
            else:
                result = await deps["browserScreenshotAction"](base_url, {
                    "targetId": target_id,
                    "fullPage": full_page,
                    "ref": ref,
                    "element": element,
                    "type": image_type,
                    "labels": labels,
                    "timeoutMs": effective_timeout_ms,
                    "profile": profile,
                })
            touch_tracked_tab(read_string_value(result.get("targetId")) if isinstance(result, dict) else target_id)
            screenshot_path = result.get("path") if isinstance(result, dict) else None
            return await deps["imageResultFromFile"]({
                "label": "browser:screenshot",
                "path": screenshot_path,
                "details": result,
            })

        if action == "navigate":
            target_url = _read_target_url_param(params)
            target_id = read_string_param(params, "targetId")
            if proxy_request:
                result = await proxy_request({"method": "POST", "path": "/navigate", "profile": profile, "body": {"url": target_url, "targetId": target_id}})
                return json_result(result)
            result = await deps["browserNavigate"](base_url, {"url": target_url, "targetId": target_id, "profile": profile})
            touch_tracked_tab(read_string_value(result.get("targetId")) if isinstance(result, dict) else target_id)
            return json_result(result)

        if action == "console":
            return await deps["executeConsoleAction"]({
                "input": params,
                "baseUrl": base_url,
                "profile": profile,
                "proxyRequest": proxy_request,
            })

        if action == "pdf":
            target_id = _normalize_optional_string(params.get("targetId"))
            if proxy_request:
                result = await proxy_request({"method": "POST", "path": "/pdf", "profile": profile, "body": {"targetId": target_id}})
            else:
                result = await deps["browserPdfSave"](base_url, {"targetId": target_id, "profile": profile})
            touch_tracked_tab(read_string_value(result.get("targetId")) if isinstance(result, dict) else target_id)
            return {"content": [{"type": "text", "text": f"FILE:{result.get('path', '')}"}], "details": result}

        if action == "upload":
            raw_paths = params.get("paths")
            paths = [str(p) for p in raw_paths] if isinstance(raw_paths, list) else []
            if not paths:
                raise RuntimeError("paths required")
            resolved_result = await deps["resolveExistingUploadPaths"]({"requestedPaths": paths})
            if not resolved_result.get("ok"):
                raise RuntimeError(resolved_result.get("error"))
            normalized_paths = resolved_result["paths"]
            ref = read_string_param(params, "ref")
            input_ref = read_string_param(params, "inputRef")
            element = read_string_param(params, "element")
            target_timeout = _read_optional_target_and_timeout(params)
            if proxy_request:
                result = await proxy_request({
                    "method": "POST", "path": "/hooks/file-chooser", "profile": profile,
                    "body": {"paths": normalized_paths, "ref": ref, "inputRef": input_ref, "element": element, **target_timeout},
                })
                return json_result(result)
            result = await deps["browserArmFileChooser"](base_url, {"paths": normalized_paths, "ref": ref, "inputRef": input_ref, "element": element, **target_timeout, "profile": profile})
            touch_tracked_tab(read_string_value(result.get("targetId")) if isinstance(result, dict) else target_timeout["targetId"])
            return json_result(result)

        if action == "dialog":
            accept = bool(params.get("accept"))
            prompt_text = read_string_value(params.get("promptText"))
            dialog_id = read_string_value(params.get("dialogId"))
            target_timeout = _read_optional_target_and_timeout(params)
            if proxy_request:
                result = await proxy_request({
                    "method": "POST", "path": "/hooks/dialog", "profile": profile,
                    "body": {"accept": accept, "promptText": prompt_text, "dialogId": dialog_id, **target_timeout},
                })
                return json_result(result)
            result = await deps["browserArmDialog"](base_url, {"accept": accept, "promptText": prompt_text, "dialogId": dialog_id, **target_timeout, "profile": profile})
            touch_tracked_tab(read_string_value(result.get("targetId")) if isinstance(result, dict) else target_timeout["targetId"])
            return json_result(result)

        if action == "act":
            request = _read_act_request_param(params)
            if not request:
                raise RuntimeError("request required")
            return await deps["executeActAction"]({
                "request": request,
                "baseUrl": base_url,
                "profile": profile,
                "proxyRequest": proxy_request,
                "onTabActivity": touch_tracked_tab,
            })

        raise RuntimeError(f"Unknown action: {action}")

    return {
        "label": "Browser",
        "name": "browser",
        "description": description,
        "parameters": BrowserToolSchema,
        "execute": execute,
    }
