"""Routes compaction through selected native agent harnesses when supported.

Full compaction credential resolution and CLI runtime alias checks are deferred
until the model-auth and model-runtime-aliases modules are ported.
"""

from __future__ import annotations

from typing import Any

from openclaw.agents.harness.policy import resolve_agent_harness_policy as resolve_configured_agent_harness_policy
from openclaw.agents.harness.selection import select_agent_harness


def _is_cli_runtime_provider(provider: str | None, *, config: Any = None) -> bool:
    try:
        from openclaw.agents.model_runtime_aliases import is_cli_runtime_provider

        return is_cli_runtime_provider(provider, config=config)
    except Exception:
        return False


def _is_cli_runtime_alias_for_provider(*, runtime: str, provider: str, cfg: Any = None) -> bool:
    try:
        from openclaw.agents.model_runtime_aliases import is_cli_runtime_alias_for_provider

        return is_cli_runtime_alias_for_provider(runtime=runtime, provider=provider, cfg=cfg)
    except Exception:
        return False


def _normalize_optional_agent_runtime_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _is_default_agent_runtime_id(value: str | None) -> bool:
    return value is None or value.strip().lower() in ("", "default", "auto")


async def maybe_compact_agent_harness_session(
    params: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    """Run harness-provided compaction when the selected runtime supports it."""
    options = options or {}
    provider = params.get("provider")
    config = params.get("config")

    if provider and _is_cli_runtime_provider(provider, config=config):
        return None

    runtime_policy_session_key = params.get("sandboxSessionKey") or params.get("sessionKey")
    runtime_policy_agent_id = params.get("agentId")
    sandbox_key = params.get("sandboxSessionKey")
    if sandbox_key and _parse_agent_session_key(sandbox_key):
        runtime_policy_agent_id = None

    runtime = resolve_configured_agent_harness_policy(
        provider=provider,
        model_id=params.get("model"),
        config=config,
        agent_id=runtime_policy_agent_id,
        session_key=runtime_policy_session_key,
    ).get("runtime", "auto")

    if _is_cli_runtime_alias_for_provider(runtime=runtime, provider=provider or "", cfg=config):
        return None

    selected_runtime = _normalize_optional_agent_runtime_id(params.get("agentHarnessId"))
    agent_harness_runtime_override = (
        selected_runtime if selected_runtime and not _is_default_agent_runtime_id(selected_runtime) else None
    )

    try:
        harness = select_agent_harness(
            {
                "provider": provider or "",
                "modelId": params.get("model"),
                "config": config,
                "agentId": runtime_policy_agent_id,
                "sessionKey": runtime_policy_session_key,
                "agentHarnessRuntimeOverride": agent_harness_runtime_override,
            }
        )
    except Exception as err:
        if agent_harness_runtime_override and "does not support" in str(err):
            return None
        raise

    should_compact_after_context_engine = options.get("nativeCompactionRequest") == "after_context_engine"
    compact_after_context_engine = getattr(harness, "compactAfterContextEngine", None)
    if should_compact_after_context_engine and compact_after_context_engine is None:
        return None

    compact_fn = getattr(harness, "compact", None)
    if not options.get("nativeCompactionRequest") and compact_fn is None:
        if getattr(harness, "id", "") != "openclaw":
            return {
                "ok": False,
                "compacted": False,
                "reason": f'Agent harness "{getattr(harness, "id", "")}" does not support compaction.',
                "failure": {"reason": "unsupported_harness_compaction"},
            }
        return None

    compact_params = {**params}
    if should_compact_after_context_engine and compact_after_context_engine is not None:
        return await compact_after_context_engine(compact_params)
    if compact_fn is not None:
        return await compact_fn(compact_params)
    return None


def _parse_agent_session_key(key: str | None) -> bool:
    if not key or not isinstance(key, str):
        return False
    return key.startswith("agent:")
