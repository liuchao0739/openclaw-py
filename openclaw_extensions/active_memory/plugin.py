from __future__ import annotations

from typing import Any


def register_active_memory_plugin(api: Any) -> None:
    from openclaw_extensions.active_memory.config import (
        ACTIVE_MEMORY_GLOBAL_MUTATION_ADMIN_REQUIRED_TEXT,
        ActiveRecallPluginConfig,
        apply_active_memory_runtime_config_snapshot,
        format_active_memory_command_help,
        has_deprecated_model_fallback_policy,
        is_active_memory_globally_enabled,
        normalize_plugin_config,
        requires_admin_to_mutate_active_memory_global,
        resolve_status_update_agent_id,
        to_single_line_log_value,
        update_active_memory_global_enabled_in_config,
    )
    from openclaw_extensions.active_memory.memory_search import (
        build_plugin_debug_line,
        build_plugin_status_line,
        build_query,
        build_recall_prompt,
        build_search_query,
        extract_recent_turns,
        build_persisted_debug_summary,
    )

    config = normalize_plugin_config(getattr(api, "plugin_config", None))

    def warn_deprecated_model_fallback_policy(plugin_config: Any) -> None:
        if has_deprecated_model_fallback_policy(plugin_config):
            logger = getattr(api, "logger", None)
            if logger:
                warn = getattr(logger, "warn", None)
                if warn:
                    warn(
                        "active-memory: config.modelFallbackPolicy is deprecated and no longer changes runtime behavior. "
                        "config.modelFallback is a chain-resolution last-resort (consulted only when config.model, "
                        "the current run's model, and the agent's configured default all resolve to nothing) — "
                        "it is NOT a runtime failover that substitutes a different model when the resolved model errors out.",
                    )

    warn_deprecated_model_fallback_policy(getattr(api, "plugin_config", None))

    def refresh_live_config_from_runtime() -> None:
        nonlocal config
        runtime = getattr(api, "runtime", None)
        config_obj = getattr(runtime, "config", None) if runtime else None
        current = getattr(config_obj, "current", None) if config_obj else None
        live_plugin_config = None
        if callable(current):
            cfg = current()
            if cfg is not None:
                from openclaw_extensions.active_memory.config import resolve_plugin_config_object
                live_plugin_config = resolve_plugin_config_object(cfg, "active-memory")
        if live_plugin_config is None:
            live_plugin_config = getattr(api, "plugin_config", {"enabled": False})
        config = normalize_plugin_config(live_plugin_config)
        if live_plugin_config:
            warn_deprecated_model_fallback_policy(live_plugin_config)

    def _persist_plugin_status_lines(
        agent_id: str,
        session_key: str | None,
        status_line: str | None = None,
        debug_summary: str | None = None,
        search_debug: Any | None = None,
    ) -> None:
        if not session_key or not session_key.strip():
            return
        agent_id = agent_id.strip()
        if not agent_id and (status_line or debug_summary):
            return
        try:
            runtime = getattr(api, "runtime", None)
            agent = getattr(runtime, "agent", None) if runtime else None
            session = getattr(agent, "session", None) if agent else None
            if session is None:
                return
            if not status_line and not debug_summary:
                try:
                    entry = session.get_session_entry(agentId=agent_id, sessionKey=session_key)
                    plugin_debug_entries = entry.get("pluginDebugEntries") if entry else None
                    has_active_memory_entry = False
                    if isinstance(plugin_debug_entries, list):
                        has_active_memory_entry = any(
                            isinstance(e, dict) and e.get("pluginId") == "active-memory"
                            for e in plugin_debug_entries
                        )
                    if not has_active_memory_entry:
                        return
                except Exception:
                    return
            debug_line = build_plugin_debug_line(
                summary=debug_summary,
                search_debug=search_debug,
            )
            next_lines: list[str] = []
            if status_line:
                next_lines.append(status_line)
            if debug_line:
                next_lines.append(debug_line)

            def _update(existing: Any) -> dict[str, Any]:
                existing_entries = []
                if isinstance(existing, dict):
                    raw_entries = existing.get("pluginDebugEntries")
                    if isinstance(raw_entries, list):
                        existing_entries = [
                            e for e in raw_entries
                            if isinstance(e, dict) and e.get("pluginId") != "active-memory"
                        ]
                if next_lines:
                    existing_entries.append({
                        "pluginId": "active-memory",
                        "lines": next_lines,
                    })
                result: dict[str, Any] = {}
                if existing_entries:
                    result["pluginDebugEntries"] = existing_entries
                return result

            session.patch_session_entry(
                agentId=agent_id,
                sessionKey=session_key,
                preserveActivity=True,
                update=_update,
            )
        except Exception as err:
            logger = getattr(api, "logger", None)
            if logger:
                debug_fn = getattr(logger, "debug", None)
                if debug_fn:
                    debug_fn(
                        f"active-memory: failed to persist session status note ({err})",
                    )

    def _maybe_resolve_active_recall(
        agent_id: str,
        session_key: str | None,
        session_id: str | None,
        message_provider: str | None,
        channel_id: str | None,
        query: str,
        search_query: str,
        current_model_provider_id: str | None = None,
        current_model_id: str | None = None,
    ) -> dict[str, Any]:
        import time

        from openclaw_extensions.active_memory.cache import (
            build_cache_key,
            get_cached_result,
            set_cached_result,
            should_cache_result,
        )
        from openclaw_extensions.active_memory.circuit_breaker import (
            build_circuit_breaker_key,
            is_circuit_breaker_open,
            record_circuit_breaker_timeout,
            reset_circuit_breaker,
        )
        from openclaw_extensions.active_memory.config import (
            ACTIVE_MEMORY_RECALL_LANE,
            HOOK_TIMEOUT_RECOVERY_GRACE_MS,
            MAX_TIMEOUT_MS,
            MAX_SETUP_GRACE_TIMEOUT_MS,
            build_prompt_prefix,
            format_elapsed_ms_compact,
            is_enabled_for_agent,
            resolve_active_memory_cleanup_config,
        )

        started_at = time.time() * 1000
        cache_key = build_cache_key(agent_id, session_key, session_id, query)
        cached = get_cached_result(cache_key)
        log_prefix_parts = [f"active-memory: agent={to_single_line_log_value(agent_id)}"]
        session_part = to_single_line_log_value(session_key or session_id or "none")
        log_prefix_parts.append(f"session={session_part}")

        if cached:
            _persist_plugin_status_lines(
                agent_id=agent_id,
                session_key=session_key,
                status_line=f"{build_plugin_status_line(cached, config)} cached",
                debug_summary=build_persisted_debug_summary(cached),
                search_debug=cached.get("searchDebug"),
            )
            if config.logging:
                logger = getattr(api, "logger", None)
                if logger:
                    info_fn = getattr(logger, "info", None)
                    if info_fn:
                        info_fn(
                            f"{' '.join(log_prefix_parts)} cached status={cached.get('status')} "
                            f"summaryChars={len(cached.get('summary', '') or '')} "
                            f"queryChars={len(query)}",
                        )
            return cached

        cb_key = build_circuit_breaker_key(agent_id, current_model_provider_id, current_model_id)
        if is_circuit_breaker_open(
            cb_key,
            config.circuit_breaker_max_timeouts,
            config.circuit_breaker_cooldown_ms,
        ):
            result = {
                "status": "timeout",
                "elapsedMs": 0,
                "summary": None,
            }
            if config.logging:
                logger = getattr(api, "logger", None)
                if logger:
                    info_fn = getattr(logger, "info", None)
                    if info_fn:
                        info_fn(
                            f"{' '.join(log_prefix_parts)} skipped (circuit breaker open after consecutive timeouts)",
                        )
            _persist_plugin_status_lines(
                agent_id=agent_id,
                session_key=session_key,
                status_line=f"{build_plugin_status_line(result, config)} circuit-breaker",
            )
            return result

        if config.logging:
            logger = getattr(api, "logger", None)
            if logger:
                info_fn = getattr(logger, "info", None)
                if info_fn:
                    info_fn(
                        f"{' '.join(log_prefix_parts)} start timeoutMs={config.timeout_ms} "
                        f"queryChars={len(query)} searchQueryChars={len(search_query)}",
                    )

        return {
            "status": "failed",
            "elapsedMs": time.time() * 1000 - started_at,
            "summary": None,
        }

    def _is_eligible_interactive_session(ctx: dict[str, Any]) -> bool:
        trigger = ctx.get("trigger")
        if trigger != "user":
            return False
        session_key = ctx.get("sessionKey", "")
        import re
        if session_key and re.match(r"^dreaming-narrative-(light|rem|deep)-", session_key, re.IGNORECASE):
            return False
        if session_key and re.match(r"^agent:[^:]+:dreaming-narrative-(light|rem|deep)-", session_key, re.IGNORECASE):
            return False
        if not ctx.get("sessionKey") and not ctx.get("sessionId"):
            return False
        provider = (ctx.get("messageProvider") or "").strip().lower()
        if provider == "webchat":
            return True
        channel_id = ctx.get("channelId")
        return bool(channel_id and str(channel_id).strip())

    def _resolve_chat_type(ctx: dict[str, Any]) -> str | None:
        session_key = (ctx.get("sessionKey") or "").strip()
        if session_key:
            import re
            if session_key.lower().startswith("agent:") and len(session_key.split(":")) > 2 and session_key.split(":")[2] == "explicit":
                return "explicit"
            if ":group:" in session_key.lower():
                return "group"
            if ":channel:" in session_key.lower():
                return "channel"
            if ":direct:" in session_key.lower() or ":dm:" in session_key.lower():
                return "direct"
        provider = (ctx.get("messageProvider") or "").strip().lower()
        if provider == "webchat":
            return "direct"
        return None

    def _is_allowed_chat_type(ctx: dict[str, Any]) -> bool:
        chat_type = _resolve_chat_type(ctx)
        if not chat_type:
            return False
        return chat_type in config.allowed_chat_types

    def _resolve_conversation_id(ctx: dict[str, Any]) -> str | None:
        session_key = (ctx.get("sessionKey") or "").strip()
        if not session_key:
            return None
        parts = session_key.split(":")
        if len(parts) < 3:
            return None
        chat_type_markers = {"direct", "dm", "group", "channel"}
        for i in range(1, len(parts)):
            if parts[i].lower() in chat_type_markers:
                return ":".join(parts[i + 1:]) or None
        return None

    def _is_allowed_chat_id(ctx: dict[str, Any]) -> bool:
        has_allowlist = len(config.allowed_chat_ids) > 0
        has_denylist = len(config.denied_chat_ids) > 0
        if not has_allowlist and not has_denylist:
            return True
        conversation_id = _resolve_conversation_id(ctx)
        if has_allowlist:
            if not conversation_id:
                return False
            if conversation_id not in config.allowed_chat_ids:
                return False
        if has_denylist and conversation_id and conversation_id in config.denied_chat_ids:
            return False
        return True

    def _register_command() -> None:
        command = {
            "name": "active-memory",
            "description": "Enable, disable, or inspect Active Memory for this session.",
            "acceptsArgs": True,
            "handler": _command_handler,
        }
        register_fn = getattr(api, "register_command", None)
        if register_fn:
            register_fn(command)

    def _command_handler(ctx: dict[str, Any]) -> dict[str, Any]:
        args_raw = ctx.get("args") or ""
        tokens = [t for t in args_raw.strip().split() if t]
        is_global = "--global" in tokens
        action = next((t for t in tokens if t != "--global"), "status").lower()

        if action == "help":
            return {"text": format_active_memory_command_help()}

        if is_global:
            current_cfg = {}
            try:
                runtime = getattr(api, "runtime", None)
                config_obj = getattr(runtime, "config", None) if runtime else None
                current_fn = getattr(config_obj, "current", None) if config_obj else None
                if callable(current_fn):
                    current_cfg = current_fn() or {}
            except Exception:
                pass

            if action == "status":
                return {
                    "text": f"Active Memory: {'on' if is_active_memory_globally_enabled(current_cfg) else 'off'} globally.",
                }

            scopes = ctx.get("gatewayClientScopes")
            if requires_admin_to_mutate_active_memory_global(scopes):
                return {"text": ACTIVE_MEMORY_GLOBAL_MUTATION_ADMIN_REQUIRED_TEXT}

            if action in ("on", "enable", "enabled"):
                try:
                    runtime = getattr(api, "runtime", None)
                    config_obj = getattr(runtime, "config", None) if runtime else None
                    mutate_fn = getattr(config_obj, "mutate_config_file", None) if config_obj else None
                    if mutate_fn:
                        def _mutate(draft: dict[str, Any]) -> None:
                            next_cfg = update_active_memory_global_enabled_in_config(draft, True)
                            draft.clear()
                            draft.update(next_cfg)
                        mutate_fn(afterWrite={"mode": "auto"}, mutate=_mutate)
                    refresh_live_config_from_runtime()
                except Exception:
                    pass
                return {"text": "Active Memory: on globally."}

            if action in ("off", "disable", "disabled"):
                try:
                    runtime = getattr(api, "runtime", None)
                    config_obj = getattr(runtime, "config", None) if runtime else None
                    mutate_fn = getattr(config_obj, "mutate_config_file", None) if config_obj else None
                    if mutate_fn:
                        def _mutate(draft: dict[str, Any]) -> None:
                            next_cfg = update_active_memory_global_enabled_in_config(draft, False)
                            draft.clear()
                            draft.update(next_cfg)
                        mutate_fn(afterWrite={"mode": "auto"}, mutate=_mutate)
                    refresh_live_config_from_runtime()
                except Exception:
                    pass
                return {"text": "Active Memory: off globally."}

        agent_id = resolve_status_update_agent_id(ctx)
        if not is_enabled_for_agent(config, agent_id):
            return {"text": "Active Memory: off for this session."}

        if action == "status":
            return {"text": f"Active Memory: on for this session."}
        if action in ("on", "enable", "enabled"):
            return {"text": "Active Memory: on for this session."}
        if action in ("off", "disable", "disabled"):
            return {"text": "Active Memory: off for this session."}

        return {
            "text": f"Unknown Active Memory action: {action}\n\n{format_active_memory_command_help()}",
        }

    _register_command()

    MAX_SEARCH_QUERY_CHARS = 480
    TIMEOUT_PARTIAL_DATA_GRACE_MS = 500
    HOOK_TIMEOUT_RECOVERY_GRACE_MS = TIMEOUT_PARTIAL_DATA_GRACE_MS + 1000

    before_prompt_build_timeout_ms = (
        MAX_TIMEOUT_MS + MAX_SETUP_GRACE_TIMEOUT_MS + HOOK_TIMEOUT_RECOVERY_GRACE_MS * 2
    )

    def _before_prompt_build_handler(event: dict[str, Any], ctx: dict[str, Any]) -> dict[str, Any] | None:
        refresh_live_config_from_runtime()
        invocation_config = config

        agent_id = resolve_status_update_agent_id(ctx)
        session_key = ctx.get("sessionKey", "") or ""
        if not session_key and agent_id:
            session_id_val = ctx.get("sessionId")
            if session_id_val:
                session_key = f"agent:{agent_id}:{session_id_val}"

        effective_agent_id = agent_id or resolve_status_update_agent_id({"sessionKey": session_key})

        if not is_enabled_for_agent(invocation_config, effective_agent_id):
            _persist_plugin_status_lines(agent_id=effective_agent_id, session_key=session_key)
            return None

        if not _is_eligible_interactive_session({**ctx, "sessionKey": session_key}):
            _persist_plugin_status_lines(agent_id=effective_agent_id, session_key=session_key)
            return None

        if not _is_allowed_chat_type({
            **ctx,
            "sessionKey": session_key,
            "mainKey": getattr(getattr(api, "config", {}), "session", {}).get("mainKey", "main") if isinstance(getattr(api, "config", {}), dict) else "main",
        }):
            _persist_plugin_status_lines(agent_id=effective_agent_id, session_key=session_key)
            return None

        if not _is_allowed_chat_id({
            "sessionKey": session_key,
            "messageProvider": ctx.get("messageProvider"),
        }):
            _persist_plugin_status_lines(agent_id=effective_agent_id, session_key=session_key)
            return None

        messages = event.get("messages") if isinstance(event, dict) else None
        prompt = event.get("prompt", "") if isinstance(event, dict) else ""
        recent_turns = extract_recent_turns(messages) if messages else []
        query = build_query(prompt, invocation_config, recent_turns)
        search_query = build_search_query(prompt, recent_turns)

        try:
            result = _maybe_resolve_active_recall(
                agent_id=effective_agent_id,
                session_key=session_key,
                session_id=ctx.get("sessionId"),
                message_provider=ctx.get("messageProvider"),
                channel_id=ctx.get("channelId"),
                query=query,
                search_query=search_query,
                current_model_provider_id=ctx.get("modelProviderId"),
                current_model_id=ctx.get("modelId"),
            )
        except Exception as err:
            logger = getattr(api, "logger", None)
            if logger:
                warn_fn = getattr(logger, "warn", None)
                if warn_fn:
                    warn_fn(f"active-memory: before_prompt_build failed, skipping memory lookup: {err}")
            return None

        summary = result.get("summary") if isinstance(result, dict) else None
        if not summary:
            return None

        from openclaw_extensions.active_memory.config import build_prompt_prefix
        prompt_prefix = build_prompt_prefix(summary)
        if not prompt_prefix:
            return None

        return {"prependContext": prompt_prefix}

    api.on(
        "before_prompt_build",
        _before_prompt_build_handler,
        {"timeoutMs": before_prompt_build_timeout_ms},
    )