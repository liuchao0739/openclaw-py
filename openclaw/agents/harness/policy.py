"""Resolves configured native harness policy for agent ids."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

AUTO_AGENT_RUNTIME_ID = "auto"

EmbeddedAgentRuntime = Literal[
    "default",
    "auto",
    "openclaw",
    "codex",
    "claude",
    "gemini",
    "openai",
]


class AgentHarnessPolicy(TypedDict, total=False):
    runtime: str
    runtimeSource: Literal["model", "provider", "implicit"]


def _normalize_optional_runtime_id(value: str | None) -> str | None:
    if value is None:
        return None
    trimmed = str(value).strip()
    return trimmed or None


def _openai_provider_uses_custom_base_url(config: dict[str, Any] | None) -> bool:
    if not config:
        return False
    models = config.get("models")
    if not isinstance(models, dict):
        return False
    providers = models.get("providers")
    if not isinstance(providers, dict):
        return False
    openai_cfg = providers.get("openai")
    if not isinstance(openai_cfg, dict):
        return False
    base = openai_cfg.get("baseUrl")
    if not isinstance(base, str) or not base.strip():
        return False
    from urllib.parse import urlparse

    try:
        url = urlparse(base.strip())
        if url.scheme != "https" or url.hostname.lower() != "api.openai.com":
            return True
        path = url.path or ""
        return path not in ("", "/", "/v1", "/v1/")
    except ValueError:
        return True


def _is_openai_provider(provider: str | None) -> bool:
    if not provider:
        return False
    return provider.strip().lower() in ("openai", "openai-codex")


def _openai_uses_codex_by_default(*, provider: str | None, config: dict[str, Any] | None) -> bool:
    return _is_openai_provider(provider) and not _openai_provider_uses_custom_base_url(config)


def resolve_agent_harness_policy(
    *,
    provider: str | None = None,
    model_id: str | None = None,
    config: dict[str, Any] | None = None,
    agent_id: str | None = None,
    session_key: str | None = None,
    env: dict[str, str] | None = None,
) -> AgentHarnessPolicy:
    del model_id, agent_id, session_key, env

    configured_runtime: str | None = None
    runtime_source: Literal["model", "provider", "implicit"] = "implicit"
    if config and isinstance(config.get("agents"), dict):
        defaults = config["agents"].get("defaults")
        if isinstance(defaults, dict):
            policy = defaults.get("runtime")
            if isinstance(policy, str):
                configured_runtime = _normalize_optional_runtime_id(policy)
                runtime_source = "provider"

    normalized = _normalize_optional_runtime_id(configured_runtime)
    runtime = normalized if normalized and normalized != "default" else AUTO_AGENT_RUNTIME_ID

    if _openai_uses_codex_by_default(provider=provider, config=config):
        if runtime == "auto":
            return {"runtime": "codex", "runtimeSource": runtime_source}
        return {"runtime": runtime, "runtimeSource": runtime_source}

    return {"runtime": runtime, "runtimeSource": runtime_source}