"""Web content provider runtime helpers shared by search and fetch tools.

Mirrors packages/web-content-core/src/provider-runtime-shared.ts.
"""

from __future__ import annotations

import os
import re
from collections.abc import Callable, Mapping
from typing import Any, Literal, TypedDict, TypeVar

from openclaw.config.secrets import normalize_secret_input_string
from openclaw.packages.normalization_core import is_record
from openclaw.utils.normalize_secret_input import normalize_secret_input

__all__ = [
    "WebProviderConfigSource",
    "has_web_provider_entry_credential",
    "provider_requires_credential",
    "read_web_provider_env_value",
    "resolve_web_provider_config",
    "resolve_web_provider_definition",
]

DEFAULT_SECRET_PROVIDER_ALIAS = "default"
ENV_SECRET_REF_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
LEGACY_SECRETREF_ENV_MARKER_PREFIX = "secretref-env:"
LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX = "__env__:"
ENV_SECRET_TEMPLATE_RE = re.compile(r"^\$\{([A-Z][A-Z0-9_]{0,127})\}$")
ENV_SECRET_SHORTHAND_RE = re.compile(r"^\$([A-Z][A-Z0-9_]{0,127})$")

WebToolKind = Literal["search", "fetch"]
SecretRefSource = Literal["env", "file", "exec"]


class SecretRef(TypedDict):
    source: SecretRefSource
    provider: str
    id: str


class WebProviderConfigSource(TypedDict, total=False):
    tools: dict[str, Any]


class RuntimeWebProviderMetadata(TypedDict, total=False):
    provider_configured: str
    selected_provider: str


class ProviderWithCredential(TypedDict, total=False):
    env_vars: list[str]
    auth_provider_id: str
    requires_credential: bool


class WebProviderCandidate(TypedDict, total=False):
    id: str


TProvider = TypeVar("TProvider", bound=ProviderWithCredential)
TProviderCandidate = TypeVar("TProviderCandidate", bound=WebProviderCandidate)
TConfigSource = TypeVar("TConfigSource", bound=WebProviderConfigSource)
TConfig = TypeVar("TConfig")
TRuntimeMetadata = TypeVar("TRuntimeMetadata", bound=RuntimeWebProviderMetadata)
TDefinition = TypeVar("TDefinition")


def _is_secret_ref(value: object) -> bool:
    if not is_record(value):
        return False
    if len(value) != 3:
        return False
    source = value.get("source")
    provider = value.get("provider")
    ref_id = value.get("id")
    return (
        source in ("env", "file", "exec")
        and isinstance(provider, str)
        and provider.strip() != ""
        and isinstance(ref_id, str)
        and ref_id.strip() != ""
    )


def _coerce_secret_ref(value: object) -> SecretRef | None:
    if _is_secret_ref(value):
        return {
            "source": value["source"],  # type: ignore[typeddict-item]
            "provider": value["provider"],  # type: ignore[typeddict-item]
            "id": value["id"],  # type: ignore[typeddict-item]
        }
    if isinstance(value, str):
        trimmed = value.strip()
        legacy_prefix: str | None = None
        if trimmed.startswith(LEGACY_SECRETREF_ENV_MARKER_PREFIX):
            legacy_prefix = LEGACY_SECRETREF_ENV_MARKER_PREFIX
        elif trimmed.startswith(LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX):
            legacy_prefix = LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX
        if legacy_prefix is not None:
            ref_id = trimmed[len(legacy_prefix) :]
            if ENV_SECRET_REF_ID_RE.fullmatch(ref_id):
                return {
                    "source": "env",
                    "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
                    "id": ref_id,
                }
            return None
        template_match = ENV_SECRET_TEMPLATE_RE.fullmatch(trimmed)
        shorthand_match = ENV_SECRET_SHORTHAND_RE.fullmatch(trimmed)
        match = template_match or shorthand_match
        if match:
            return {
                "source": "env",
                "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
                "id": match.group(1),
            }
        return None
    if (
        is_record(value)
        and value.get("source") in ("env", "file", "exec")
        and isinstance(value.get("id"), str)
        and value["id"].strip() != ""
        and value.get("provider") is None
    ):
        return {
            "source": value["source"],  # type: ignore[typeddict-item]
            "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
            "id": value["id"],  # type: ignore[typeddict-item]
        }
    return None


def resolve_web_provider_config(
    cfg: WebProviderConfigSource | None,
    kind: WebToolKind,
) -> dict[str, Any] | None:
    tools = cfg.get("tools") if cfg else None
    if not is_record(tools):
        return None
    web_config = tools.get("web")
    if not is_record(web_config):
        return None
    tool_config = web_config.get(kind)
    if not is_record(tool_config):
        return None
    return dict(tool_config)


def read_web_provider_env_value(
    env_vars: list[str],
    process_env: Mapping[str, str | None] | None = None,
) -> str | None:
    env = process_env if process_env is not None else os.environ
    for env_var in env_vars:
        value = normalize_secret_input(env.get(env_var))
        if value:
            return value
    return None


def provider_requires_credential(provider: ProviderWithCredential) -> bool:
    return provider.get("requires_credential") is not False


def has_web_provider_entry_credential(
    *,
    provider: TProvider,
    config: TConfigSource | None,
    tool_config: TConfig,
    resolve_raw_value: Callable[..., Any],
    resolve_fallback_raw_value: Callable[..., Any] | None = None,
    resolve_env_value: Callable[..., str | None],
    resolve_provider_auth_value: Callable[[str], bool] | None = None,
) -> bool:
    if not provider_requires_credential(provider):
        return True
    raw_value = resolve_raw_value(
        provider=provider,
        config=config,
        tool_config=tool_config,
    )
    configured_ref = _coerce_secret_ref(raw_value)
    if configured_ref and configured_ref["source"] != "env":
        return True
    from_config = normalize_secret_input(normalize_secret_input_string(raw_value) or "")
    if from_config:
        return True
    auth_provider_id = provider.get("auth_provider_id")
    if auth_provider_id and resolve_provider_auth_value and resolve_provider_auth_value(
        auth_provider_id
    ):
        return True
    configured_env_var_id = (
        configured_ref["id"] if configured_ref and configured_ref["source"] == "env" else None
    )
    if resolve_env_value(
        provider=provider,
        configured_env_var_id=configured_env_var_id,
    ):
        return True
    fallback_raw_value = (
        resolve_fallback_raw_value(
            provider=provider,
            config=config,
            tool_config=tool_config,
        )
        if resolve_fallback_raw_value
        else None
    )
    fallback_ref = _coerce_secret_ref(fallback_raw_value)
    if fallback_ref and fallback_ref["source"] != "env":
        return True
    fallback_config = normalize_secret_input(normalize_secret_input_string(fallback_raw_value) or "")
    if fallback_config:
        return True
    if fallback_ref and fallback_ref["source"] == "env":
        return bool(
            resolve_env_value(
                provider=provider,
                configured_env_var_id=fallback_ref["id"],
            )
        )
    return False


def resolve_web_provider_definition(
    *,
    config: TConfigSource | None,
    tool_config: TConfig,
    runtime_metadata: TRuntimeMetadata | None,
    providers: list[TProviderCandidate],
    resolve_enabled: Callable[..., bool],
    resolve_auto_provider_id: Callable[..., str],
    create_tool: Callable[..., TDefinition | None],
    sandboxed: bool | None = None,
    provider_id: str | None = None,
    resolve_fallback_provider_id: Callable[..., str | None] | None = None,
) -> dict[str, Any] | None:
    if not resolve_enabled(tool_config=tool_config, sandboxed=sandboxed):
        return None
    filtered_providers = [entry for entry in providers if entry]
    if not filtered_providers:
        return None
    auto_provider_id = resolve_auto_provider_id(
        config=config,
        tool_config=tool_config,
        providers=filtered_providers,
    )
    selected_provider_id = (
        provider_id
        or (runtime_metadata.get("selected_provider") if runtime_metadata else None)
        or auto_provider_id
    )
    if not selected_provider_id:
        return None
    provider = next(
        (entry for entry in filtered_providers if entry.get("id") == selected_provider_id),
        None,
    )
    if provider is None and resolve_fallback_provider_id:
        fallback_provider_id = resolve_fallback_provider_id(
            config=config,
            tool_config=tool_config,
            providers=filtered_providers,
            provider_id=selected_provider_id,
        )
        if fallback_provider_id:
            provider = next(
                (entry for entry in filtered_providers if entry.get("id") == fallback_provider_id),
                None,
            )
    if provider is None:
        return None
    definition = create_tool(
        provider=provider,
        config=config,
        tool_config=tool_config,
        runtime_metadata=runtime_metadata,
    )
    if definition is None:
        return None
    return {"provider": provider, "definition": definition}
