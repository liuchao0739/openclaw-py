import os
import re
from typing import Any, Callable, Dict, List, Literal, Optional, TypedDict


class WebProviderConfigSource(TypedDict, total=False):
    tools: Dict[str, Any]


SecretRefSource = Literal["env", "file", "exec"]


class SecretRef(TypedDict):
    source: SecretRefSource
    provider: str
    id: str


DEFAULT_SECRET_PROVIDER_ALIAS = "default"
ENV_SECRET_REF_ID_RE = re.compile(r"^[A-Z][A-Z0-9_]{0,127}$")
LEGACY_SECRETREF_ENV_MARKER_PREFIX = "secretref-env:"
LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX = "__env__:"
ENV_SECRET_TEMPLATE_RE = re.compile(r"^\$\{([A-Z][A-Z0-9_]{0,127})\}$")
ENV_SECRET_SHORTHAND_RE = re.compile(r"^\$([A-Z][A-Z0-9_]{0,127})$")


class RuntimeWebProviderMetadata(TypedDict, total=False):
    providerConfigured: str
    selectedProvider: str


class ProviderWithCredential(TypedDict, total=False):
    envVars: List[str]
    authProviderId: str
    requiresCredential: bool


WebContentProcessEnv = Dict[str, Optional[str]]


def _is_record(value: Any) -> bool:
    return isinstance(value, dict)


def _normalize_secret_input_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if len(trimmed) > 0 else None


def _normalize_secret_input(value: Any) -> str:
    if not isinstance(value, str):
        return ""
    collapsed = re.sub(r"[\r\n\u2028\u2029]+", "", value)
    latin1_only = ""
    for char in collapsed:
        code_point = ord(char)
        if code_point <= 0xFF:
            latin1_only += char
    return latin1_only.strip()


def _is_secret_ref(value: Any) -> bool:
    if not _is_record(value):
        return False
    if len(value) != 3:
        return False
    return (
        value.get("source") in ("env", "file", "exec")
        and isinstance(value.get("provider"), str)
        and len(value["provider"].strip()) > 0
        and isinstance(value.get("id"), str)
        and len(value["id"].strip()) > 0
    )


def _coerce_secret_ref(value: Any) -> Optional[SecretRef]:
    if _is_secret_ref(value):
        return value
    if isinstance(value, str):
        trimmed = value.strip()
        legacy_prefix = None
        if trimmed.startswith(LEGACY_SECRETREF_ENV_MARKER_PREFIX):
            legacy_prefix = LEGACY_SECRETREF_ENV_MARKER_PREFIX
        elif trimmed.startswith(LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX):
            legacy_prefix = LEGACY_DOUBLE_UNDERSCORE_ENV_MARKER_PREFIX
        if legacy_prefix:
            id_part = trimmed[len(legacy_prefix):]
            if ENV_SECRET_REF_ID_RE.match(id_part):
                return {"source": "env", "provider": DEFAULT_SECRET_PROVIDER_ALIAS, "id": id_part}
            return None
        match = ENV_SECRET_TEMPLATE_RE.match(trimmed) or ENV_SECRET_SHORTHAND_RE.match(trimmed)
        if match:
            return {"source": "env", "provider": DEFAULT_SECRET_PROVIDER_ALIAS, "id": match.group(1)}
        return None
    if (
        _is_record(value)
        and value.get("source") in ("env", "file", "exec")
        and isinstance(value.get("id"), str)
        and len(value["id"].strip()) > 0
        and value.get("provider") is None
    ):
        return {
            "source": value["source"],
            "provider": DEFAULT_SECRET_PROVIDER_ALIAS,
            "id": value["id"],
        }
    return None


def resolve_web_provider_config(
    cfg: Optional[WebProviderConfigSource],
    kind: Literal["search", "fetch"],
) -> Optional[Dict[str, Any]]:
    tools = cfg.get("tools") if cfg else None
    if not tools or not isinstance(tools, dict):
        return None
    web_config = tools.get("web")
    if not web_config or not isinstance(web_config, dict):
        return None
    tool_config = web_config.get(kind)
    if not tool_config or not isinstance(tool_config, dict):
        return None
    return tool_config


def read_web_provider_env_value(
    env_vars: List[str],
    process_env: Optional[WebContentProcessEnv] = None,
) -> Optional[str]:
    if process_env is None:
        process_env = {k: os.environ.get(k) for k in os.environ}
    for env_var in env_vars:
        value = _normalize_secret_input(process_env.get(env_var))
        if value:
            return value
    return None


def provider_requirescredential(provider: ProviderWithCredential) -> bool:
    return provider.get("requiresCredential") is not False


def has_web_provider_entry_credential(
    provider: ProviderWithCredential,
    config: Optional[WebProviderConfigSource],
    tool_config: Optional[Dict[str, Any]],
    resolve_raw_value: Callable[[], Any],
    resolve_env_value: Callable[[Optional[str]], Optional[str]],
    resolve_fallback_raw_value: Optional[Callable[[], Any]] = None,
    resolve_provider_auth_value: Optional[Callable[[str], bool]] = None,
) -> bool:
    if not provider_requirescredential(provider):
        return True
    raw_value = resolve_raw_value()
    configured_ref = _coerce_secret_ref(raw_value)
    if configured_ref and configured_ref["source"] != "env":
        return True
    from_config = _normalize_secret_input(_normalize_secret_input_string(raw_value))
    if from_config:
        return True
    if provider.get("authProviderId") and resolve_provider_auth_value:
        if resolve_provider_auth_value(provider["authProviderId"]):
            return True
    configured_env_var_id = configured_ref["id"] if configured_ref and configured_ref["source"] == "env" else None
    if resolve_env_value(configured_env_var_id):
        return True
    if resolve_fallback_raw_value:
        fallback_raw_value = resolve_fallback_raw_value()
        fallback_ref = _coerce_secret_ref(fallback_raw_value)
        if fallback_ref and fallback_ref["source"] != "env":
            return True
        fallback_config = _normalize_secret_input(_normalize_secret_input_string(fallback_raw_value))
        if fallback_config:
            return True
        if fallback_ref and fallback_ref["source"] == "env":
            if resolve_env_value(fallback_ref["id"]):
                return True
    return False


def resolve_web_provider_definition(
    config: Optional[WebProviderConfigSource],
    tool_config: Optional[Dict[str, Any]],
    runtime_metadata: Optional[RuntimeWebProviderMetadata],
    providers: List[Any],
    resolve_enabled: Callable[[Optional[Dict[str, Any]], Optional[bool]], bool],
    resolve_auto_provider_id: Callable[..., str],
    create_tool: Callable[..., Any],
    sandboxed: Optional[bool] = None,
    provider_id: Optional[str] = None,
    resolve_fallback_provider_id: Optional[Callable[..., Optional[str]]] = None,
) -> Optional[dict]:
    if not resolve_enabled(tool_config, sandboxed):
        return None
    filtered_providers = [p for p in providers if p]
    if len(filtered_providers) == 0:
        return None
    auto_provider_id = resolve_auto_provider_id(
        config=config,
        tool_config=tool_config,
        providers=filtered_providers,
    )
    resolved_provider_id = provider_id or (runtime_metadata or {}).get("selectedProvider") or auto_provider_id
    if not resolved_provider_id:
        return None
    provider = next((p for p in filtered_providers if p.get("id") == resolved_provider_id), None)
    if not provider and resolve_fallback_provider_id:
        fallback_id = resolve_fallback_provider_id(
            config=config,
            tool_config=tool_config,
            providers=filtered_providers,
            provider_id=resolved_provider_id,
        )
        if fallback_id:
            provider = next((p for p in filtered_providers if p.get("id") == fallback_id), None)
    if not provider:
        return None
    definition = create_tool(
        provider=provider,
        config=config,
        tool_config=tool_config,
        runtime_metadata=runtime_metadata,
    )
    if not definition:
        return None
    return {"provider": provider, "definition": definition}
