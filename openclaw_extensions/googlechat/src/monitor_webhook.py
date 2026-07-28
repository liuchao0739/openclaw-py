from __future__ import annotations

import re
from typing import Any

from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty
from openclaw.plugin_sdk.webhook_ingress import (
    WEBHOOK_RATE_LIMIT_DEFAULTS,
    normalize_webhook_path,
    resolve_request_client_ip,
)
from openclaw.plugin_sdk.webhook_request_guards import (
    WebhookInFlightLimiter,
    read_json_webhook_body_or_reject,
)
from openclaw.plugin_sdk.webhook_targets import (
    resolve_webhook_target_with_auth_or_reject,
    with_resolved_webhook_request_pipeline,
)
from openclaw_extensions.googlechat.src.auth import verify_google_chat_request
from openclaw_extensions.googlechat.src.monitor_types import WebhookTarget
from openclaw_extensions.googlechat.src.types import (
    GoogleChatAction,
    GoogleChatEvent,
    GoogleChatMessage,
    GoogleChatSpace,
    GoogleChatUser,
)

ADD_ON_PREAUTH_MAX_BYTES = 16 * 1024
ADD_ON_PREAUTH_TIMEOUT_MS = 3000


def _extract_bearer_token(header: Any) -> str:
    if isinstance(header, list):
        auth_header = header[0] if len(header) > 0 else ""
    elif isinstance(header, str):
        auth_header = header
    else:
        auth_header = ""
    if not isinstance(auth_header, str):
        return ""
    if auth_header.lower().startswith("bearer "):
        return auth_header[len("bearer "):].strip()
    return ""


def _record_params_to_action_parameters(params: dict | None = None) -> list | None:
    if not params:
        return None
    entries = [(k, v) for k, v in params.items() if isinstance(v, str)]
    return [{"key": k, "value": v} for k, v in entries] if entries else None


def _parse_google_chat_inbound_payload(raw: Any, res: Any) -> dict:
    if not raw or not isinstance(raw, dict) or isinstance(raw, list):
        if hasattr(res, "status_code"):
            res.status_code = 400
        if hasattr(res, "end"):
            res.end("invalid payload")
        return {"ok": False}

    event_payload = raw
    add_on_bearer_token = ""

    raw_obj = raw
    if raw_obj.get("commonEventObject", {}).get("hostApp") == "CHAT":
        token = raw_obj.get("authorizationEventObject", {}).get("systemIdToken", "")
        add_on_bearer_token = token.strip() if isinstance(token, str) else ""

    if raw_obj.get("commonEventObject", {}).get("hostApp") == "CHAT":
        chat = raw_obj.get("chat", {})
        if chat and chat.get("messagePayload"):
            message_payload = chat["messagePayload"]
            event_payload = {
                "type": "MESSAGE",
                "space": message_payload.get("space"),
                "message": message_payload.get("message"),
                "user": chat.get("user"),
                "eventTime": chat.get("eventTime"),
            }
        elif chat and chat.get("buttonClickedPayload"):
            button_clicked_payload = chat["buttonClickedPayload"]
            invoked_function = raw_obj.get("commonEventObject", {}).get("invokedFunction")
            action_parameters = _record_params_to_action_parameters(
                raw_obj.get("commonEventObject", {}).get("parameters")
            )
            event_payload = {
                "type": "CARD_CLICKED",
                "space": button_clicked_payload.get("space"),
                "message": button_clicked_payload.get("message"),
                "user": button_clicked_payload.get("user") or chat.get("user"),
                "eventTime": chat.get("eventTime"),
                "action": button_clicked_payload.get("action") or (
                    {
                        **({"actionMethodName": invoked_function} if isinstance(invoked_function, str) else {}),
                        **({"parameters": action_parameters} if action_parameters else {}),
                    }
                ),
                "commonEventObject": {
                    **({"invokedFunction": invoked_function} if isinstance(invoked_function, str) else {}),
                    "parameters": raw_obj.get("commonEventObject", {}).get("parameters"),
                },
            }

    event = event_payload
    event_type = event.get("type") or event_payload.get("eventType")
    if not isinstance(event_type, str):
        if hasattr(res, "status_code"):
            res.status_code = 400
        if hasattr(res, "end"):
            res.end("invalid payload")
        return {"ok": False}

    space = event.get("space")
    if not space or not isinstance(space, dict) or isinstance(space, list):
        if hasattr(res, "status_code"):
            res.status_code = 400
        if hasattr(res, "end"):
            res.end("invalid payload")
        return {"ok": False}

    if event_type == "MESSAGE":
        message = event.get("message")
        if not message or not isinstance(message, dict) or isinstance(message, list):
            if hasattr(res, "status_code"):
                res.status_code = 400
            if hasattr(res, "end"):
                res.end("invalid payload")
            return {"ok": False}
    elif event_type == "CARD_CLICKED":
        user = event.get("user")
        if not user or not isinstance(user, dict) or isinstance(user, list):
            if hasattr(res, "status_code"):
                res.status_code = 400
            if hasattr(res, "end"):
                res.end("invalid payload")
            return {"ok": False}

    return {"ok": True, "event": event, "addOnBearerToken": add_on_bearer_token}


async def _verify_google_chat_target_auth(target: WebhookTarget, bearer: str) -> dict:
    verification = await verify_google_chat_request({
        "bearer": bearer,
        "audienceType": target.get("audienceType"),
        "audience": target.get("audience"),
        "expectedAddOnPrincipal": target["account"].config.get("appPrincipal"),
    })
    if verification.get("ok"):
        return {"ok": True}
    return {"ok": False, "reason": verification.get("reason", "unknown")}


def _log_google_chat_webhook_auth_rejections(rejections: list) -> None:
    for rejection in rejections:
        rejection["target"]["runtime"].get("log", lambda m: None)(
            f"[{rejection['target']['account'].account_id}] Google Chat webhook auth rejected: {rejection['reason']}"
        )


def _log_google_chat_webhook_auth_rejected_for_targets(targets: list, reason: str) -> None:
    _log_google_chat_webhook_auth_rejections([{"target": t, "reason": reason} for t in targets])


async def _resolve_google_chat_webhook_target_with_auth_or_reject(params: dict) -> WebhookTarget | None:
    targets = params.get("targets", [])
    bearer = params.get("bearer", "")
    rejections = []
    verified_count = 0

    async def _is_match(target):
        return _verify_google_chat_target_auth(target, bearer).get("ok", False)

    selected_target = await resolve_webhook_target_with_auth_or_reject({
        "targets": targets,
        "res": params.get("res"),
        "isMatch": _is_match,
    })

    if not selected_target and verified_count == 0:
        _log_google_chat_webhook_auth_rejections(rejections)
    return selected_target


def warn_app_principal_misconfiguration(params: dict) -> None:
    if params.get("audienceType") != "app-url":
        return
    principal = (params.get("appPrincipal") or "").strip()
    log_fn = params.get("log", lambda m: None)
    if not principal:
        log_fn(
            f'[{params.get("accountId")}] appPrincipal is missing for audienceType "app-url"; '
            f"add-on token verification will fail. Set appPrincipal to the numeric OAuth 2.0 client ID (uniqueId, 21 digits), not an email."
        )
    elif "@" in principal:
        log_fn(
            f'[{params.get("accountId")}] appPrincipal "{principal}" looks like an email address. '
            f"Set appPrincipal to the numeric OAuth 2.0 client ID (uniqueId, 21 digits), not an email."
        )


def create_google_chat_webhook_request_handler(params: dict):
    webhook_targets = params["webhookTargets"]
    webhook_rate_limiter = params["webhookRateLimiter"]
    webhook_in_flight_limiter = params["webhookInFlightLimiter"]
    process_event = params["processEvent"]

    async def handler(req, res) -> bool:
        path = normalize_webhook_path(req.url.pathname if hasattr(req, "url") else "/")
        config = None
        path_targets = webhook_targets.get(path, [])
        if path_targets:
            config = path_targets[0].get("config")

        client_ip = resolve_request_client_ip(
            req,
            config.get("gateway", {}).get("trustedProxies") if config else None,
            config.get("gateway", {}).get("allowRealIpFallback", False) if config else False,
        ) or "unknown"

        async def _handle(params_inner: dict) -> dict:
            targets = params_inner.get("targets", [])
            header_bearer = _extract_bearer_token(
                req.headers.get("authorization") if hasattr(req, "headers") else None
            )
            selected_target = None
            parsed_event = None

            async def _read_and_parse_event(profile: str) -> dict | None:
                extra = {}
                if profile == "pre-auth":
                    extra = {
                        "maxBytes": ADD_ON_PREAUTH_MAX_BYTES,
                        "timeoutMs": ADD_ON_PREAUTH_TIMEOUT_MS,
                    }
                body_result = await read_json_webhook_body_or_reject(
                    req, res, profile, emptyObjectOnEmpty=False, invalidJsonMessage="invalid payload", **extra
                )
                if not body_result.get("ok"):
                    return None
                parsed = _parse_google_chat_inbound_payload(body_result["value"], res)
                return parsed if parsed.get("ok") else None

            if header_bearer:
                selected_target = await _resolve_google_chat_webhook_target_with_auth_or_reject({
                    "targets": targets,
                    "res": res,
                    "bearer": header_bearer,
                })
                if not selected_target:
                    return {"handled": True}
                parsed = await _read_and_parse_event("post-auth")
                if not parsed:
                    return {"handled": True}
                parsed_event = parsed["event"]
            else:
                parsed = await _read_and_parse_event("pre-auth")
                if not parsed:
                    return {"handled": True}
                parsed_event = parsed["event"]
                if not parsed.get("addOnBearerToken"):
                    _log_google_chat_webhook_auth_rejected_for_targets(targets, "missing token")
                    if hasattr(res, "status_code"):
                        res.status_code = 401
                    if hasattr(res, "end"):
                        res.end("unauthorized")
                    return {"handled": True}
                selected_target = await _resolve_google_chat_webhook_target_with_auth_or_reject({
                    "targets": targets,
                    "res": res,
                    "bearer": parsed["addOnBearerToken"],
                })
                if not selected_target:
                    return {"handled": True}

            if not selected_target or not parsed_event:
                if hasattr(res, "status_code"):
                    res.status_code = 401
                if hasattr(res, "end"):
                    res.end("unauthorized")
                return {"handled": True}

            dispatch_target = selected_target
            if dispatch_target.get("statusSink"):
                dispatch_target["statusSink"]({"lastInboundAt": __import__("time").time() * 1000})

            async def _process():
                try:
                    await process_event(parsed_event, dispatch_target)
                except Exception as err:
                    dispatch_target["runtime"].get("error", lambda m: None)(
                        f"[{dispatch_target['account'].account_id}] Google Chat webhook failed: {err}"
                    )

            __import__("asyncio").create_task(_process())

            if hasattr(res, "status_code"):
                res.status_code = 200
            if hasattr(res, "set_header"):
                res.set_header("Content-Type", "application/json")
            if hasattr(res, "end"):
                res.end("{}")
            return {"handled": True}

        return await with_resolved_webhook_request_pipeline({
            "req": req,
            "res": res,
            "targetsByPath": webhook_targets,
            "allowMethods": ["POST"],
            "requireJsonContentType": True,
            "rateLimiter": webhook_rate_limiter,
            "rateLimitKey": f"{path}:{client_ip}",
            "inFlightLimiter": webhook_in_flight_limiter,
            "handle": _handle,
        })

    return handler


__all__ = [
    "warn_app_principal_misconfiguration",
    "create_google_chat_webhook_request_handler",
]