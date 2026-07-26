"""GitHub Copilot agent harness registration and lazy runtime boundaries."""
# ruff: noqa: BLE001, S110

from __future__ import annotations

import asyncio
import importlib
import math
import re
import time
from typing import Any, Literal

from openclaw.agents.harness.prompt_compaction_hook_helpers import (
    run_agent_harness_after_compaction_hook,
    run_agent_harness_before_compaction_hook,
)
from openclaw_extensions.copilot.harness_support import (
    build_agent_hook_context_channel_fields,
    compact_with_safety_timeout,
    get_model_provider_request_transport,
    resolve_compaction_timeout_ms,
    throw_if_aborted,
)
from openclaw_extensions.copilot.src.auth_bridge import (
    create_copilot_byok_auth,
    resolve_copilot_auth,
    token_fingerprint,
)
from openclaw_extensions.copilot.src.provider_bridge import (
    is_copilot_byok_unsupported_provider_error,
    resolve_copilot_provider,
    supports_copilot_byok_provider_shape,
)

COPILOT_PROVIDER_IDS = frozenset({"github-copilot"})

DeferredCompactionCleanupOutcome = Literal["aborted", "completed", "deadline"]


class AggregateError(Exception):
    def __init__(self, errors: list[BaseException], message: str) -> None:
        super().__init__(message)
        self.errors = errors


def _read_session_string(value: object) -> str | None:
    if isinstance(value, str):
        trimmed = value.strip()
        return trimmed if trimmed else None
    return None


def _fingerprint_session_value(value: object) -> str:
    return token_fingerprint(value) if isinstance(value, str) and value else ""


def _read_agent_id_from_session_key(session_key: object) -> str | None:
    if not isinstance(session_key, str):
        return None
    parts = session_key.strip().split(":")
    if parts[0] == "agent" and len(parts) > 1 and parts[1].strip():
        return parts[1].strip()
    return None


def _session_auth_fields(auth: dict[str, Any]) -> dict[str, Any]:
    auth_mode = auth.get("authMode")
    if auth_mode in ("gitHubToken", "byok"):
        return {
            "authMode": auth_mode,
            "authProfileId": auth.get("authProfileId"),
            "authProfileVersion": auth.get("authProfileVersion"),
        }
    return {"authMode": "useLoggedInUser"}


def _session_auth_matches(stored: dict[str, Any], current: dict[str, Any]) -> bool:
    if stored.get("authMode") != current.get("authMode"):
        return False
    if stored.get("authMode") == "useLoggedInUser":
        return True
    return (
        stored.get("authMode") == current.get("authMode")
        and stored.get("authProfileId") == current.get("authProfileId")
        and stored.get("authProfileVersion") == current.get("authProfileVersion")
    )


def _normalize_binding(value: dict[str, Any] | None) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    if value.get("schemaVersion") != 2:
        return None
    sdk_session_id = _read_session_string(value.get("sdkSessionId"))
    compat_key = _read_session_string(value.get("compatKey"))
    compact_key = _read_session_string(value.get("compactKey"))
    auth_mode = value.get("authMode")
    updated_at = value.get("updatedAt")
    if (
        not sdk_session_id
        or not compat_key
        or not compact_key
        or auth_mode not in ("gitHubToken", "byok", "useLoggedInUser")
        or (
            auth_mode in ("gitHubToken", "byok")
            and (
                not _read_session_string(value.get("authProfileId"))
                or not _read_session_string(value.get("authProfileVersion"))
            )
        )
        or not isinstance(updated_at, (int, float))
        or math.isnan(float(updated_at))
    ):
        return None
    binding: dict[str, Any] = {
        "schemaVersion": 2,
        "sdkSessionId": sdk_session_id,
        "compatKey": compat_key,
        "compactKey": compact_key,
        "authMode": auth_mode,
        "updatedAt": updated_at,
    }
    if auth_mode in ("gitHubToken", "byok"):
        binding["authProfileId"] = _read_session_string(value.get("authProfileId"))
        binding["authProfileVersion"] = _read_session_string(value.get("authProfileVersion"))
    return binding


def _normalize_attempt_binding(value: object) -> dict[str, Any] | None:
    current = _normalize_binding(value if isinstance(value, dict) else None)
    if current:
        return {"compatKey": current["compatKey"], "sdkSessionId": current["sdkSessionId"]}
    if not isinstance(value, dict):
        return None
    if value.get("schemaVersion") != 1:
        return None
    sdk_session_id = _read_session_string(value.get("sdkSessionId"))
    compat_key = _read_session_string(value.get("compatKey"))
    updated_at = value.get("updatedAt")
    if (
        not sdk_session_id
        or not compat_key
        or not isinstance(updated_at, (int, float))
        or math.isnan(float(updated_at))
    ):
        return None
    return {"sdkSessionId": sdk_session_id, "compatKey": compat_key}


def _lookup_stored_binding(store: Any, key: str) -> dict[str, Any] | None:
    try:
        return _normalize_attempt_binding(store.lookup(key) if store is not None else None)
    except Exception:
        try:
            if store is not None:
                store.delete(key)
        except Exception:
            pass
        return None


def _register_stored_binding(store: Any, key: str, binding: dict[str, Any]) -> bool:
    try:
        if store is not None:
            store.register(key, binding)
        return True
    except Exception:
        try:
            if store is not None:
                store.delete(key)
        except Exception:
            pass
        return False


def _delete_stored_binding(store: Any, key: str) -> bool:
    try:
        if store is not None:
            store.delete(key)
        return True
    except Exception:
        return False


def _is_stale_sdk_session_error(error: object) -> bool:
    message = str(error)
    return bool(
        re.search(
            r"\b(404|not found|no such session|unknown session|stale|deleted|does not exist)\b",
            message,
            re.IGNORECASE,
        )
    )


def _normalize_auth_override(auth: object) -> dict[str, Any] | None:
    if not isinstance(auth, dict):
        return None
    return {
        "use_logged_in_user": auth.get("useLoggedInUser") is True or auth.get("use_logged_in_user") is True,
        "git_hub_token": auth.get("gitHubToken") or auth.get("git_hub_token"),
        "profile_id": auth.get("profileId") or auth.get("profile_id"),
        "profile_version": auth.get("profileVersion") or auth.get("profile_version"),
    }


def _read_param(params: dict[str, Any], *keys: str) -> str | None:
    for key in keys:
        value = _read_session_string(params.get(key))
        if value:
            return value
    return None


def _compute_session_key(params: dict[str, Any], *, include_api: bool, include_auth: bool) -> str:
    model_obj: dict[str, Any]
    raw_model = params.get("model")
    runtime_model = params.get("runtimeModel") or params.get("runtime_model")
    if isinstance(raw_model, dict):
        model_obj = raw_model
    elif isinstance(runtime_model, dict):
        model_obj = runtime_model
    else:
        model_obj = {"id": raw_model if isinstance(raw_model, str) else None}

    provider = model_obj.get("provider") or params.get("provider") or ""
    if isinstance(provider, str):
        provider = provider.strip()
    model_id = (
        model_obj.get("id")
        or params.get("modelId")
        or params.get("model_id")
        or (raw_model if isinstance(raw_model, str) else "")
    )
    request_transport = (
        get_model_provider_request_transport(model_obj) if isinstance(raw_model, dict) else None
    )
    request_auth_mode = _read_session_string(
        (request_transport or {}).get("auth", {}).get("mode")
        if isinstance((request_transport or {}).get("auth"), dict)
        else None
    ) or _read_session_string(
        model_obj.get("request", {}).get("auth", {}).get("mode")
        if isinstance(model_obj.get("request"), dict)
        and isinstance(model_obj.get("request", {}).get("auth"), dict)
        else None
    )
    azure_api_version = _read_session_string(
        model_obj.get("azureApiVersion")
        or model_obj.get("azure_api_version")
        or (
            model_obj.get("params", {}).get("azureApiVersion")
            if isinstance(model_obj.get("params"), dict)
            else None
        )
    )

    auth_parts: list[str]
    resolved_agent_id = ""
    resolved_copilot_home = ""
    try:
        if not include_auth:
            resolved = resolve_copilot_auth(
                {
                    "agent_id": _read_param(params, "agentId", "agent_id")
                    or _read_agent_id_from_session_key(params.get("sessionKey")),
                    "agent_dir": _read_param(params, "agentDir", "agent_dir"),
                    "workspace_dir": _read_param(params, "workspaceDir", "workspace_dir"),
                    "copilot_home": _read_param(params, "copilotHome", "copilot_home"),
                    "auth": {"use_logged_in_user": True},
                }
            )
            auth_parts = []
        else:
            model_provider = resolve_copilot_provider(
                model={
                    "api": model_obj.get("api"),
                    "id": model_id,
                    "provider": provider,
                    "base_url": model_obj.get("baseUrl") or model_obj.get("base_url"),
                    "azure_api_version": azure_api_version,
                    "headers": model_obj.get("headers"),
                    "auth_header": model_obj.get("authHeader") or model_obj.get("auth_header"),
                    "request_auth_mode": request_auth_mode,
                    "request_proxy": (request_transport or {}).get("proxy")
                    or (
                        model_obj.get("request", {}).get("proxy")
                        if isinstance(model_obj.get("request"), dict)
                        else None
                    ),
                    "request_tls": (request_transport or {}).get("tls")
                    or (
                        model_obj.get("request", {}).get("tls")
                        if isinstance(model_obj.get("request"), dict)
                        else None
                    ),
                    "request_allow_private_network": (request_transport or {}).get("allowPrivateNetwork")
                    or (
                        model_obj.get("request", {}).get("allowPrivateNetwork")
                        if isinstance(model_obj.get("request"), dict)
                        else None
                    ),
                    "context_tokens": model_obj.get("contextTokens") or model_obj.get("context_tokens"),
                    "context_window": model_obj.get("contextWindow") or model_obj.get("context_window"),
                    "max_tokens": model_obj.get("maxTokens") or model_obj.get("max_tokens"),
                },  # type: ignore[arg-type]
                resolved_api_key=_read_param(params, "resolvedApiKey", "resolved_api_key"),
                auth_profile_id=_read_param(params, "authProfileId", "auth_profile_id"),
            )
            if model_provider.get("mode") == "byok":
                resolved = create_copilot_byok_auth(
                    agent_id=_read_param(params, "agentId", "agent_id")
                    or _read_agent_id_from_session_key(params.get("sessionKey")),
                    agent_dir=_read_param(params, "agentDir", "agent_dir"),
                    workspace_dir=_read_param(params, "workspaceDir", "workspace_dir"),
                    copilot_home=_read_param(params, "copilotHome", "copilot_home"),
                    auth_profile_id=model_provider.get("auth_profile_id"),
                    auth_profile_version=model_provider.get("auth_profile_version"),
                )
            else:
                resolved = resolve_copilot_auth(
                    {
                        "agent_id": _read_param(params, "agentId", "agent_id")
                        or _read_agent_id_from_session_key(params.get("sessionKey")),
                        "agent_dir": _read_param(params, "agentDir", "agent_dir"),
                        "workspace_dir": _read_param(params, "workspaceDir", "workspace_dir"),
                        "copilot_home": _read_param(params, "copilotHome", "copilot_home"),
                        "auth": _normalize_auth_override(params.get("auth")),
                        "resolved_api_key": _read_param(params, "resolvedApiKey", "resolved_api_key"),
                        "auth_profile_id": _read_param(params, "authProfileId", "auth_profile_id"),
                        "profile_version": _read_param(params, "profileVersion", "profile_version"),
                    }
                )
            auth_parts = [
                f"auth.mode={resolved['auth_mode']}",
                f"auth.profileId={resolved.get('auth_profile_id', '')}",
                f"auth.profileVersion={resolved.get('auth_profile_version', '')}",
            ]
        resolved_agent_id = resolved["agent_id"]
        resolved_copilot_home = resolved["copilot_home"]
        if not include_auth:
            auth_parts = []
    except Exception:
        auth_parts = ["auth=unresolvable"]

    parts = [
        f"provider={provider}",
        f"model={model_id}",
        *([f"api={model_obj.get('api', '')}"] if include_api else []),
        *(
            [f"baseUrlFingerprint={_fingerprint_session_value(model_obj.get('baseUrl') or model_obj.get('base_url'))}"]
            if include_api
            else []
        ),
        f"cwd={params.get('cwd') or params.get('workspaceDir') or params.get('workspace_dir') or ''}",
        f"agentId={resolved_agent_id}",
        f"agentDir={params.get('agentDir') or params.get('agent_dir') or ''}",
        f"copilotHome={params.get('copilotHome') or params.get('copilot_home') or ''}",
        f"resolvedCopilotHome={resolved_copilot_home}",
        *(auth_parts if include_auth else []),
    ]
    return "|".join(str(part) for part in parts)


def _compute_session_compat_key(params: dict[str, Any]) -> str:
    return _compute_session_key(params, include_api=True, include_auth=True)


def _compute_session_compact_key(params: dict[str, Any]) -> str:
    return _compute_session_key(params, include_api=False, include_auth=False)


def _build_copilot_compaction_hook_context(params: dict[str, Any]) -> dict[str, Any]:
    ctx: dict[str, Any] = {
        "agentId": params.get("agentId"),
        "sessionKey": params.get("sessionKey"),
        "sessionId": params.get("sessionId"),
        "workspaceDir": params.get("workspaceDir"),
        "modelProviderId": params.get("provider"),
        "modelId": params.get("model"),
        "trigger": params.get("trigger"),
        **build_agent_hook_context_channel_fields(params),
    }
    if params.get("runId"):
        ctx["runId"] = params["runId"]
    return ctx


async def _compact_tracked_sdk_session(params: dict[str, Any]) -> dict[str, Any]:
    throw_if_aborted(params.get("abortSignal"))
    client = params["client"]
    resume_kwargs: dict[str, Any] = {
        **params["sessionConfig"],
        "continuePendingWork": False,
        "suppressResumeEvent": True,
    }
    if params.get("gitHubToken"):
        resume_kwargs["gitHubToken"] = params["gitHubToken"]
    session = await client.resumeSession(params["sdkSessionId"], resume_kwargs)
    on_session = params.get("onSession")
    if callable(on_session):
        on_session(session)
    request = (
        {"customInstructions": params["customInstructions"]}
        if _read_session_string(params.get("customInstructions"))
        else None
    )
    try:
        throw_if_aborted(params.get("abortSignal"))
        history = getattr(getattr(getattr(session, "rpc", None), "history", None), "compact", None)
        if history is None and isinstance(session, dict):
            history = session.get("rpc", {}).get("history", {}).get("compact")
        if callable(history):
            result = history(request)
            if asyncio.iscoroutine(result):
                return await result
            return result
        raise RuntimeError("copilot session missing history.compact")
    finally:
        disconnect = getattr(session, "disconnect", None)
        if disconnect is None and isinstance(session, dict):
            disconnect = session.get("disconnect")
        if callable(disconnect):
            try:
                disconnect_result = disconnect()
                if asyncio.iscoroutine(disconnect_result):
                    await disconnect_result
            except Exception:
                pass


def create_copilot_agent_harness(options: dict[str, Any] | None = None) -> dict[str, Any]:
    """Create the GitHub Copilot agent harness used for attempts and compaction."""
    options = options or {}
    created_pool: Any = None
    pool_lock = asyncio.Lock()
    disposed = False
    dispose_promise: asyncio.Task[None] | None = None
    in_flight: set[asyncio.Task[Any]] = set()
    deferred_compaction_cleanups: dict[str, dict[asyncio.Future[Any], dict[str, Any]]] = {}
    tracked_sessions: dict[str, dict[str, Any]] = {}
    reset_blocked_stored_sessions: set[str] = set()

    async def get_pool() -> Any:
        nonlocal created_pool
        if options.get("pool") is not None:
            return options["pool"]
        if created_pool is not None:
            return created_pool
        async with pool_lock:
            if created_pool is None:
                runtime = importlib.import_module("openclaw_extensions.copilot.src.runtime")
                created_pool = runtime.create_copilot_client_pool(options.get("poolOptions"))
        return created_pool

    def track_deferred_compaction_cleanup(params: dict[str, Any]) -> None:
        session_id = params["sessionId"]
        cleanup = params["cleanup"]
        cleanups = deferred_compaction_cleanups.setdefault(session_id, {})
        cleanups[cleanup] = {
            "abort": params["abort"],
            "sdkSessionId": params["sdkSessionId"],
        }

        def _remove(_: Any) -> None:
            remove_deferred_compaction_cleanup(session_id, cleanup)

        cleanup.add_done_callback(_remove)

    def remove_deferred_compaction_cleanup(session_id: str, cleanup: asyncio.Future[Any]) -> None:
        cleanups = deferred_compaction_cleanups.get(session_id)
        if not cleanups:
            return
        cleanups.pop(cleanup, None)
        if not cleanups:
            deferred_compaction_cleanups.pop(session_id, None)

    def has_pending_deferred_compaction_cleanup(session_id: str) -> bool:
        cleanups = deferred_compaction_cleanups.get(session_id)
        if not cleanups:
            return False
        current_sdk_session_id = tracked_sessions.get(session_id, {}).get("sdkSessionId") or (
            _lookup_stored_binding(options.get("sessionStore"), session_id) or {}
        ).get("sdkSessionId")
        if current_sdk_session_id is None:
            return False
        return any(entry["sdkSessionId"] == current_sdk_session_id for entry in cleanups.values())

    async def abort_deferred_compaction_cleanups(session_id: str) -> None:
        cleanups = deferred_compaction_cleanups.get(session_id)
        if not cleanups:
            return
        pending = list(cleanups.items())
        for _, cleanup in pending:
            cleanup["abort"]()
        await asyncio.gather(*[cleanup for cleanup, _ in pending], return_exceptions=True)

    def supports(ctx: dict[str, Any]) -> dict[str, Any]:
        requested_runtime = str(ctx.get("requestedRuntime") or "").strip().lower()
        if requested_runtime != "copilot":
            return {"supported": False, "reason": "copilot is opt-in only"}
        provider = str(ctx.get("provider") or "").strip().lower()
        if not provider:
            return {"supported": False, "reason": "provider is required"}
        if provider in COPILOT_PROVIDER_IDS:
            return {"supported": True, "priority": 100}
        provider_owner_status = ctx.get("providerOwnerStatus")
        provider_owner_plugin_ids = ctx.get("providerOwnerPluginIds")
        if (
            provider_owner_status != "unowned"
            or not isinstance(provider_owner_plugin_ids, list)
            or len(provider_owner_plugin_ids) > 0
        ):
            ordered = ", ".join(sorted(COPILOT_PROVIDER_IDS))
            return {"supported": False, "reason": f"provider is not one of: {ordered}"}
        model_provider = ctx.get("modelProvider")
        if not isinstance(model_provider, dict):
            model_provider = {}
        request = model_provider.get("request") if isinstance(model_provider.get("request"), dict) else {}
        if not supports_copilot_byok_provider_shape(
            {
                "api": model_provider.get("api"),
                "base_url": model_provider.get("baseUrl"),
                "request_proxy": request.get("proxy"),
                "request_tls": request.get("tls"),
                "request_allow_private_network": request.get("allowPrivateNetwork"),
            }
        ):
            return {
                "supported": False,
                "reason": (
                    "provider is not a supported Copilot BYOK model "
                    "(requires supported api, baseUrl, and no request transport policy overrides)"
                ),
            }
        return {"supported": True, "priority": 100}

    async def run_attempt(params: dict[str, Any]) -> Any:
        if disposed:
            raise RuntimeError("[copilot] harness has been disposed; cannot start new attempts")

        async def _attempt() -> Any:
            attempt_module = importlib.import_module("openclaw_extensions.copilot.src.attempt")
            if disposed:
                raise RuntimeError("[copilot] harness was disposed while starting an attempt")
            pool = await get_pool()
            if disposed:
                raise RuntimeError("[copilot] harness was disposed while starting an attempt")
            try:
                pool_acquire = attempt_module.resolve_pool_acquire(params)
            except Exception as error:
                if is_copilot_byok_unsupported_provider_error(error):
                    return await attempt_module.run_copilot_attempt(params, {"pool": pool})
                raise
            openclaw_session_id = params.get("sessionId") if isinstance(params.get("sessionId"), str) else None
            current_compat_key = _compute_session_compat_key(params)
            current_compact_key = _compute_session_compact_key(params)
            compaction_cleanup_pending = (
                openclaw_session_id is not None and has_pending_deferred_compaction_cleanup(openclaw_session_id)
            )
            replay_blocked = openclaw_session_id is not None and (
                compaction_cleanup_pending or openclaw_session_id in reset_blocked_stored_sessions
            )
            tracked = (
                tracked_sessions.get(openclaw_session_id)
                if openclaw_session_id and not replay_blocked
                else None
            )
            stored = (
                None
                if replay_blocked
                else _lookup_stored_binding(options.get("sessionStore"), openclaw_session_id)
                if openclaw_session_id
                else None
            )
            resumable_session_id = (
                tracked["sdkSessionId"]
                if tracked and tracked.get("compatKey") == current_compat_key
                else stored["sdkSessionId"]
                if not tracked and stored and stored.get("compatKey") == current_compat_key
                else None
            )
            effective_params = (
                {
                    **params,
                    "initialReplayState": {
                        **(params.get("initialReplayState") or {}),
                        "sdkSessionId": resumable_session_id,
                    },
                }
                if resumable_session_id
                else params
            )

            def on_session_established(info: dict[str, Any]) -> None:
                if not openclaw_session_id:
                    return
                tracked_sessions[openclaw_session_id] = {
                    "sdkSessionId": info["sdkSessionId"],
                    "client": info["pooledClient"]["client"],
                    "clientOptions": pool_acquire["options"],
                    "compatKey": current_compat_key,
                    "compactKey": current_compact_key,
                    "poolKey": info["pooledClient"]["key"],
                    "sessionConfig": info.get("compactionSessionConfig") or info.get("sessionConfig"),
                    **_session_auth_fields(pool_acquire["auth"]),
                }
                _register_stored_binding(
                    options.get("sessionStore"),
                    openclaw_session_id,
                    {
                        "schemaVersion": 2,
                        "sdkSessionId": info["sdkSessionId"],
                        "compatKey": current_compat_key,
                        "compactKey": current_compact_key,
                        **_session_auth_fields(pool_acquire["auth"]),
                        "updatedAt": int(time.time() * 1000),
                    },
                )
                reset_blocked_stored_sessions.discard(openclaw_session_id)

            def on_deferred_compaction(info: dict[str, Any]) -> None:
                if not openclaw_session_id:
                    return
                tracked_binding = tracked_sessions.get(openclaw_session_id)
                stored_binding = _lookup_stored_binding(options.get("sessionStore"), openclaw_session_id)
                owns_tracked = tracked_binding and tracked_binding.get("sdkSessionId") == info["sdkSessionId"]
                owns_stored = stored_binding and stored_binding.get("sdkSessionId") == info["sdkSessionId"]
                if not owns_tracked and not owns_stored:
                    return
                cleanup_future = _ensure_future(info["cleanup"])
                track_deferred_compaction_cleanup(
                    {
                        "abort": info["abort"],
                        "cleanup": cleanup_future,
                        "sessionId": openclaw_session_id,
                        "sdkSessionId": info["sdkSessionId"],
                    }
                )
                reset_blocked_stored_sessions.add(openclaw_session_id)

                def _on_cleanup_done(fut: asyncio.Future[Any]) -> None:
                    try:
                        outcome = fut.result()
                    except Exception:
                        outcome = "aborted"
                    current_tracked = tracked_sessions.get(openclaw_session_id)
                    current_stored = _lookup_stored_binding(options.get("sessionStore"), openclaw_session_id)
                    still_tracked = (
                        current_tracked and current_tracked.get("sdkSessionId") == info["sdkSessionId"]
                    )
                    still_stored = current_stored and current_stored.get("sdkSessionId") == info["sdkSessionId"]
                    if outcome == "completed":
                        if still_tracked or still_stored:
                            reset_blocked_stored_sessions.discard(openclaw_session_id)
                        return
                    if still_tracked:
                        tracked_sessions.pop(openclaw_session_id, None)
                    if still_stored:
                        _delete_stored_binding(options.get("sessionStore"), openclaw_session_id)
                    if still_tracked or still_stored:
                        reset_blocked_stored_sessions.add(openclaw_session_id)

                cleanup_future.add_done_callback(_on_cleanup_done)

            deps: dict[str, Any] = {"pool": pool}
            if openclaw_session_id:
                deps["onSessionEstablished"] = on_session_established
                deps["onDeferredCompaction"] = on_deferred_compaction
            return await attempt_module.run_copilot_attempt(effective_params, deps)

        task = asyncio.create_task(_attempt())
        in_flight.add(task)
        try:
            return await task
        finally:
            in_flight.discard(task)

    async def reset(params: dict[str, Any]) -> None:
        openclaw_session_id = params.get("sessionId") if isinstance(params.get("sessionId"), str) else None
        if not openclaw_session_id:
            return
        tracked = tracked_sessions.get(openclaw_session_id)
        stored = _lookup_stored_binding(options.get("sessionStore"), openclaw_session_id)
        reset_blocked_stored_sessions.add(openclaw_session_id)
        await abort_deferred_compaction_cleanups(openclaw_session_id)
        current_stored = _lookup_stored_binding(options.get("sessionStore"), openclaw_session_id)
        still_owns_stored = (
            stored is not None
            and current_stored is not None
            and current_stored.get("sdkSessionId") == stored.get("sdkSessionId")
        )
        if still_owns_stored:
            if _delete_stored_binding(options.get("sessionStore"), openclaw_session_id):
                reset_blocked_stored_sessions.discard(openclaw_session_id)
        else:
            reset_blocked_stored_sessions.discard(openclaw_session_id)
        if not tracked:
            return
        if tracked_sessions.get(openclaw_session_id, {}).get("sdkSessionId") == tracked.get("sdkSessionId"):
            tracked_sessions.pop(openclaw_session_id, None)
        try:
            await tracked["client"].deleteSession(tracked["sdkSessionId"])
        except Exception:
            pass

    async def compact(params: dict[str, Any]) -> dict[str, Any] | None:
        openclaw_session_id = params.get("sessionId") if isinstance(params.get("sessionId"), str) else None
        if not openclaw_session_id:
            return {"ok": False, "compacted": False, "reason": "missing-required-params"}
        if has_pending_deferred_compaction_cleanup(openclaw_session_id):
            return {
                "ok": False,
                "compacted": False,
                "reason": "background-compaction-pending",
                "failure": {"reason": "background-compaction-pending"},
            }
        tracked = tracked_sessions.get(openclaw_session_id)
        current_compact_key = _compute_session_compact_key(params)
        attempt_module = importlib.import_module("openclaw_extensions.copilot.src.attempt")
        resolved_pool_acquire: dict[str, Any] | None = None
        try:
            resolved_pool_acquire = attempt_module.resolve_pool_acquire(params)
        except Exception as error:
            if is_copilot_byok_unsupported_provider_error(error):
                return {
                    "ok": False,
                    "compacted": False,
                    "reason": "missing_thread_binding",
                    "failure": {"reason": "missing_thread_binding"},
                }
            raise
        current_auth = _session_auth_fields(resolved_pool_acquire["auth"])
        compatible_tracked = (
            tracked
            if tracked
            and tracked.get("compactKey") == current_compact_key
            and _session_auth_matches(tracked, current_auth)
            else None
        )
        if not compatible_tracked:
            return {
                "ok": False,
                "compacted": False,
                "reason": "missing_thread_binding",
                "failure": {"reason": "missing_thread_binding"},
            }
        pool_acquire = {
            "key": compatible_tracked["poolKey"],
            "options": compatible_tracked["clientOptions"],
        }
        compact_result: dict[str, Any] | None = None
        handle: Any = None
        pool: Any = None
        active_sdk_session: Any = None
        cleanup_byok_proxy: Any = None
        hook_context = _build_copilot_compaction_hook_context(params)
        try:
            throw_if_aborted(params.get("abortSignal"))
            pool = await get_pool()
            handle = await pool.acquire(pool_acquire["key"], pool_acquire["options"])
            client = handle["client"] if isinstance(handle, dict) else handle.client
            byok_proxy = None
            if compatible_tracked.get("authMode") == "byok" and compatible_tracked.get("sessionConfig", {}).get(
                "provider"
            ):
                byok_proxy_module = importlib.import_module("openclaw_extensions.copilot.src.byok_proxy")
                byok_proxy = await byok_proxy_module.create_copilot_byok_proxy(
                    {
                        "mode": "byok",
                        "provider": compatible_tracked["sessionConfig"]["provider"],
                    }
                )
            cleanup_byok_proxy = (
                byok_proxy.get("close")
                if isinstance(byok_proxy, dict)
                else getattr(byok_proxy, "close", None)
            )
            session_config = compatible_tracked["sessionConfig"]
            provider_override = (
                byok_proxy.get("provider", {}).get("provider")
                if isinstance(byok_proxy, dict)
                else getattr(getattr(byok_proxy, "provider", None), "provider", None)
            )
            if provider_override:
                session_config = {**compatible_tracked["sessionConfig"], "provider": provider_override}
            await run_agent_harness_before_compaction_hook(
                {"sessionFile": params["sessionFile"], "ctx": hook_context}
            )

            def _capture_session(session: Any) -> None:
                nonlocal active_sdk_session
                active_sdk_session = session

            async def _compact_call(abort_signal: Any = None) -> dict[str, Any]:
                return await _compact_tracked_sdk_session(
                    {
                        "abortSignal": abort_signal or params.get("abortSignal"),
                        "client": client,
                        "customInstructions": params.get("customInstructions"),
                        "gitHubToken": compatible_tracked.get("clientOptions", {}).get("gitHubToken")
                        or (
                            resolved_pool_acquire["auth"].get("gitHubToken")
                            if resolved_pool_acquire["auth"].get("authMode") == "gitHubToken"
                            else None
                        ),
                        "onSession": _capture_session,
                        "sessionConfig": session_config,
                        "sdkSessionId": compatible_tracked["sdkSessionId"],
                    }
                )

            def _on_cancel() -> None:
                if active_sdk_session is None:
                    return
                abort_manual = getattr(
                    getattr(getattr(active_sdk_session, "rpc", None), "history", None),
                    "abortManualCompaction",
                    None,
                )
                if callable(abort_manual):
                    result = abort_manual()
                    if asyncio.iscoroutine(result):
                        asyncio.create_task(result)

            compact_result = await compact_with_safety_timeout(
                _compact_call,
                resolve_compaction_timeout_ms(params.get("config") if isinstance(params.get("config"), dict) else None),
                {
                    "abortSignal": params.get("abortSignal"),
                    "onCancel": _on_cancel,
                },
            )
        except Exception as err:
            raw_error = str(err)
            if _is_stale_sdk_session_error(err):
                tracked_sessions.pop(openclaw_session_id, None)
                _delete_stored_binding(options.get("sessionStore"), openclaw_session_id)
                return {
                    "ok": False,
                    "compacted": False,
                    "reason": "stale_thread_binding",
                    "failure": {"reason": "stale_thread_binding", "rawError": raw_error},
                }
            return {
                "ok": False,
                "compacted": False,
                "reason": "copilot-sdk-history-compact-failed",
                "failure": {"reason": "copilot-sdk-history-compact-failed", "rawError": raw_error},
            }
        finally:
            if callable(cleanup_byok_proxy):
                await cleanup_byok_proxy()
            if pool is not None and handle is not None:
                try:
                    await pool.release(handle)
                except Exception:
                    pass

        if compact_result is None or not compact_result.get("success"):
            return {
                "ok": False,
                "compacted": False,
                "reason": "copilot-sdk-history-compact-failed",
                "failure": {"reason": "copilot-sdk-history-compact-failed"},
            }
        compacted = (compact_result.get("tokensRemoved") or 0) > 0 or (compact_result.get("messagesRemoved") or 0) > 0
        if compacted:
            await run_agent_harness_after_compaction_hook(
                {
                    "sessionFile": params["sessionFile"],
                    "compactedCount": compact_result.get("messagesRemoved") or 0,
                    "ctx": hook_context,
                }
            )
        result: dict[str, Any] = {
            "ok": True,
            "compacted": compacted,
            "reason": "copilot-sdk-history-compacted" if compacted else "already under target",
        }
        if compacted:
            context_window = compact_result.get("contextWindow") or {}
            result["result"] = {
                "summary": compact_result.get("summaryContent") or "",
                "firstKeptEntryId": "",
                "tokensBefore": params.get("currentTokenCount")
                or (context_window.get("currentTokens") or 0) + (compact_result.get("tokensRemoved") or 0),
                "tokensAfter": context_window.get("currentTokens"),
                "details": compact_result,
                "sessionId": params.get("sessionId"),
                "sessionFile": params.get("sessionFile"),
            }
        return result

    async def dispose() -> None:
        nonlocal dispose_promise, disposed
        if dispose_promise is not None:
            await dispose_promise
            return
        disposed = True

        async def _dispose() -> None:
            if in_flight:
                await asyncio.gather(*list(in_flight), return_exceptions=True)
            for session_id in list(deferred_compaction_cleanups.keys()):
                await abort_deferred_compaction_cleanups(session_id)
            tracked_sessions.clear()
            reset_blocked_stored_sessions.clear()
            if created_pool is not None:
                errors = await created_pool.dispose()
                if errors:
                    raise AggregateError(errors, "[copilot] pool disposal errors")

        dispose_promise = asyncio.create_task(_dispose())
        await dispose_promise

    return {
        "id": options.get("id") or "copilot",
        "label": options.get("label") or "GitHub Copilot agent runtime",
        "supports": supports,
        "runAttempt": run_attempt,
        "reset": reset,
        "compact": compact,
        "dispose": dispose,
    }


def _ensure_future(value: Any) -> asyncio.Future[Any]:
    if asyncio.isfuture(value):
        return value
    loop = asyncio.get_running_loop()
    future: asyncio.Future[Any] = loop.create_future()
    if isinstance(value, asyncio.Task):
        value.add_done_callback(lambda task: _copy_future_result(task, future))
    else:

        async def _wrap() -> Any:
            if asyncio.iscoroutine(value):
                return await value
            return value

        asyncio.create_task(_wrap_future(_wrap(), future))
    return future


def _copy_future_result(source: asyncio.Future[Any], target: asyncio.Future[Any]) -> None:
    if source.cancelled():
        target.cancel()
        return
    exc = source.exception()
    if exc is not None:
        target.set_exception(exc)
    else:
        target.set_result(source.result())


async def _wrap_future(coro: Any, future: asyncio.Future[Any]) -> None:
    try:
        future.set_result(await coro)
    except Exception as error:
        future.set_exception(error)
