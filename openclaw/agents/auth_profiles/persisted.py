from __future__ import annotations

from typing import Any

from openclaw.agents.auth_profiles.constants import AUTH_STORE_VERSION
from openclaw.agents.auth_profiles.types import (
    AuthProfileCredential,
    AuthProfileSecretsStore,
    AuthProfileState,
    AuthProfileStateStore,
    AuthProfileStore,
    OAuthCredential,
)
from openclaw.normalization_core.number_coercion import as_finite_number
from openclaw.normalization_core.record_coerce import is_record
from openclaw.normalization_core.string_coerce import normalize_optional_string
from openclaw.normalization_core.string_normalization import unique_strings


AUTH_PROFILE_TYPES = {"api_key", "oauth", "token"}


def _normalize_credential_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_expiry_field(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, (int, float)) and value > 0:
        return int(value)
    return None


def _normalize_credential_metadata(value: Any) -> dict[str, str] | None:
    if not is_record(value):
        return None
    metadata: dict[str, str] = {}
    for key, entry in value.items():
        if isinstance(entry, str):
            metadata[key] = entry
    return metadata or None


def _normalize_common_credential_fields(
    entry: dict[str, Any],
) -> dict[str, Any]:
    from openclaw.utils.boolean import as_boolean

    provider = entry.get("provider", "")
    if isinstance(provider, str):
        from openclaw.model_catalog_core.provider_id import normalize_provider_id
        provider = normalize_provider_id(provider) or ""

    normalized: dict[str, Any] = {"provider": provider}
    copy_to_agents = as_boolean(entry.get("copyToAgents"))
    if copy_to_agents is not None:
        normalized["copyToAgents"] = copy_to_agents
    email = _normalize_credential_string(entry.get("email"))
    if email is not None:
        normalized["email"] = email
    display_name = _normalize_credential_string(entry.get("displayName"))
    if display_name is not None:
        normalized["displayName"] = display_name
    return normalized


def _normalize_raw_credential_entry(
    raw: dict[str, Any],
) -> dict[str, Any]:
    entry = dict(raw)

    if "type" not in entry and isinstance(entry.get("mode"), str):
        entry["type"] = entry["mode"]
    if entry.get("type") == "apiKey":
        entry["type"] = "api_key"
    if "key" not in entry and "keyRef" not in entry:
        api_key_val = entry.get("apiKey")
        if isinstance(api_key_val, str):
            entry["key"] = api_key_val

    if entry.get("type") == "api_key":
        normalized = {
            "type": "api_key",
            **_normalize_common_credential_fields(entry),
        }
        key = _normalize_credential_string(entry.get("key"))
        key_ref = entry.get("keyRef") if isinstance(entry.get("keyRef"), dict) else None
        metadata = _normalize_credential_metadata(entry.get("metadata"))
        if key_ref:
            normalized["keyRef"] = key_ref
        elif key is not None:
            normalized["key"] = key
        if metadata:
            normalized["metadata"] = metadata
        return normalized

    if entry.get("type") == "token":
        normalized = {
            "type": "token",
            **_normalize_common_credential_fields(entry),
        }
        token = _normalize_credential_string(entry.get("token"))
        token_ref = entry.get("tokenRef") if isinstance(entry.get("tokenRef"), dict) else None
        expires = _normalize_expiry_field(entry.get("expires"))
        if token is not None:
            normalized["token"] = token
        if token_ref:
            normalized["tokenRef"] = token_ref
        if expires is not None:
            normalized["expires"] = expires
        return normalized

    if entry.get("type") == "oauth":
        normalized = {
            "type": "oauth",
            **_normalize_common_credential_fields(entry),
        }
        for field in (
            "access", "refresh", "idToken", "clientId",
            "enterpriseUrl", "projectId", "accountId", "chatgptPlanType",
        ):
            val = _normalize_credential_string(entry.get(field))
            if val is not None:
                normalized[field] = val
        expires = _normalize_expiry_field(entry.get("expires"))
        if expires is not None:
            normalized["expires"] = expires
        return normalized

    return entry


def _parse_credential_entry(
    raw: Any,
    fallback_provider: str | None = None,
) -> tuple[bool, Any]:
    if not is_record(raw):
        return False, "non_object"
    typed = _normalize_raw_credential_entry(raw)
    if typed.get("type") not in AUTH_PROFILE_TYPES:
        return False, "invalid_type"
    provider = typed.get("provider") or fallback_provider or ""
    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    normalized_provider = normalize_provider_id(provider) or ""
    if not normalized_provider:
        return False, "missing_provider"
    typed["provider"] = normalized_provider
    return True, typed


def coerce_persisted_auth_profile_store(
    raw: Any,
) -> AuthProfileStore | None:
    if not is_record(raw):
        return None
    record = raw
    if not is_record(record.get("profiles")):
        return None
    profiles = record["profiles"]
    normalized: dict[str, AuthProfileCredential] = {}
    for key, value in profiles.items():
        ok, result = _parse_credential_entry(value)
        if not ok:
            continue
        normalized[key] = result

    version = int(record.get("version", AUTH_STORE_VERSION))
    if version <= 0:
        version = AUTH_STORE_VERSION

    from openclaw.agents.auth_profiles.state import coerce_auth_profile_state
    state = coerce_auth_profile_state(raw)

    result: AuthProfileStore = {
        "version": version,
        "profiles": normalized,
    }
    if state.get("order"):
        result["order"] = state["order"]
    if state.get("lastGood"):
        result["lastGood"] = state["lastGood"]
    if state.get("usageStats"):
        result["usageStats"] = state["usageStats"]
    return result


def _merge_record(
    base: dict[str, Any] | None,
    override: dict[str, Any] | None,
) -> dict[str, Any] | None:
    if not base and not override:
        return None
    if not base:
        return dict(override)
    if not override:
        return dict(base)
    return {**base, **override}


def _group_profile_ids_by_provider(
    profiles: dict[str, AuthProfileCredential],
) -> dict[str, list[str]]:
    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    grouped: dict[str, list[str]] = {}
    for profile_id, credential in profiles.items():
        provider_key = normalize_provider_id(credential.get("provider", "")) or ""
        grouped.setdefault(provider_key, []).append(profile_id)
    return grouped


def _find_order_entry_key(
    order: dict[str, list[str]] | None,
    provider_key: str,
) -> str | None:
    if not order:
        return None
    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    for key in order:
        if normalize_provider_id(key) == provider_key:
            return key
    return None


def _merge_profile_records_with_override_precedence(
    base_profiles: dict[str, AuthProfileCredential],
    override_profiles: dict[str, AuthProfileCredential],
) -> dict[str, AuthProfileCredential]:
    override_ids = set(override_profiles.keys())
    result: dict[str, AuthProfileCredential] = {}
    for pid, cred in override_profiles.items():
        result[pid] = cred
    for pid, cred in base_profiles.items():
        if pid not in override_ids:
            result[pid] = cred
    return result


def _merge_profile_order_with_override_precedence(
    base_order: dict[str, list[str]] | None,
    override_order: dict[str, list[str]] | None,
    override_profiles: dict[str, AuthProfileCredential],
) -> dict[str, list[str]] | None:
    merged_order = _merge_record(base_order, override_order)
    if not merged_order:
        return None

    from openclaw.model_catalog_core.provider_id import normalize_provider_id
    for provider_key, override_profile_ids in _group_profile_ids_by_provider(
        override_profiles
    ).items():
        base_order_key = _find_order_entry_key(base_order, provider_key)
        override_order_key = _find_order_entry_key(override_order, provider_key)
        merged_order_key = override_order_key or base_order_key
        if not merged_order_key:
            continue

        for provider in list(merged_order.keys()):
            if provider != merged_order_key and normalize_provider_id(provider) == provider_key:
                del merged_order[provider]

        if override_order_key:
            merged_order[merged_order_key] = unique_strings(
                override_order.get(override_order_key, [])
            )
            continue

        base_order_ids = base_order.get(base_order_key, []) if base_order_key else []
        merged_order[merged_order_key] = unique_strings(
            override_profile_ids + base_order_ids + merged_order.get(merged_order_key, [])
        )

    return merged_order


def merge_auth_profile_stores(
    base: AuthProfileStore,
    override: AuthProfileStore,
    preserve_base_runtime_external_profiles: bool = False,
) -> AuthProfileStore:
    override_profiles = override.get("profiles", {})
    override_order = override.get("order")
    override_last_good = override.get("lastGood")
    override_usage_stats = override.get("usageStats")

    if (
        not override_profiles
        and not override_order
        and not override_last_good
        and not override_usage_stats
        and override.get("runtimePersistedProfileIds") is None
        and override.get("runtimeExternalProfileIds") is None
        and override.get("runtimeExternalProfileIdsAuthoritative") is not True
    ):
        return base

    override_profile_ids = set(override_profiles.keys())
    override_runtime_external_ids = set(override.get("runtimeExternalProfileIds", []))
    removed_runtime_external_ids: set[str] = set()
    if override.get("runtimeExternalProfileIdsAuthoritative") is True and not preserve_base_runtime_external_profiles:
        base_external = base.get("runtimeExternalProfileIds", [])
        removed_runtime_external_ids = {
            pid for pid in base_external
            if pid not in override_runtime_external_ids and pid not in override_profile_ids
        }

    profiles = _merge_profile_records_with_override_precedence(
        base.get("profiles", {}), override_profiles
    )
    for pid in removed_runtime_external_ids:
        profiles.pop(pid, None)

    merged_order = _merge_profile_order_with_override_precedence(
        base.get("order"), override_order or {}, override_profiles
    )
    order = None
    if merged_order:
        order = {}
        for provider, profile_ids in merged_order.items():
            filtered = [
                pid for pid in profile_ids
                if pid in profiles or pid not in removed_runtime_external_ids
            ]
            if filtered:
                order[provider] = filtered

    merged_last_good = _merge_record(base.get("lastGood"), override_last_good)
    last_good = None
    if merged_last_good:
        last_good = {
            k: v for k, v in merged_last_good.items() if v in profiles
        }

    merged_usage_stats = _merge_record(base.get("usageStats"), override_usage_stats)
    usage_stats = None
    if merged_usage_stats:
        usage_stats = {
            k: v for k, v in merged_usage_stats.items() if k in profiles
        }

    merged: AuthProfileStore = {
        "version": max(base.get("version", 0), override.get("version", 0)),
        "profiles": profiles,
    }
    if order:
        merged["order"] = order
    if last_good:
        merged["lastGood"] = last_good
    if usage_stats:
        merged["usageStats"] = usage_stats

    _rp_candidates = [pid for pid in base.get("runtimePersistedProfileIds", []) if pid not in override_profile_ids] + [pid for pid in override.get("runtimePersistedProfileIds", [])]
    runtime_persisted = sorted(set(pid for pid in _rp_candidates if pid in merged["profiles"]))
    if runtime_persisted:
        merged["runtimePersistedProfileIds"] = runtime_persisted

    base_runtime_external = []
    if not (override.get("runtimeExternalProfileIdsAuthoritative") is True and not preserve_base_runtime_external_profiles):
        base_runtime_external = [
            pid for pid in base.get("runtimeExternalProfileIds", [])
            if pid not in override_profile_ids
        ]

    _re_candidates = base_runtime_external + [pid for pid in override.get("runtimeExternalProfileIds", [])]
    runtime_external = sorted(set(pid for pid in _re_candidates if pid in merged["profiles"]))
    if runtime_external:
        merged["runtimeExternalProfileIds"] = runtime_external

    if (
        base.get("runtimeExternalProfileIdsAuthoritative") is True
        or override.get("runtimeExternalProfileIdsAuthoritative") is True
    ):
        merged["runtimeExternalProfileIdsAuthoritative"] = True

    return merged


def build_persisted_auth_profile_secrets_store(
    store: AuthProfileStore,
    should_persist_profile: Any = None,
) -> AuthProfileSecretsStore:
    profiles: dict[str, AuthProfileCredential] = {}
    for profile_id, credential in store.get("profiles", {}).items():
        if should_persist_profile and not should_persist_profile({
            "profileId": profile_id,
            "credential": credential,
        }):
            continue
        if credential.get("type") == "api_key" and credential.get("keyRef") and credential.get("key") is not None:
            sanitized = dict(credential)
            sanitized.pop("key", None)
            profiles[profile_id] = sanitized
        elif credential.get("type") == "token" and credential.get("tokenRef") and credential.get("token") is not None:
            sanitized = dict(credential)
            sanitized.pop("token", None)
            profiles[profile_id] = sanitized
        else:
            profiles[profile_id] = credential

    return {"version": AUTH_STORE_VERSION, "profiles": profiles}


def load_persisted_auth_profile_store(
    agent_dir: str | None = None,
    database: Any = None,
) -> AuthProfileStore | None:
    from openclaw.agents.auth_profiles.sqlite import read_persisted_auth_profile_store_raw
    raw = read_persisted_auth_profile_store_raw(agent_dir, database)
    store = coerce_persisted_auth_profile_store(raw)
    if not store:
        return None
    from openclaw.agents.auth_profiles.state import (
        coerce_auth_profile_state,
        load_persisted_auth_profile_state,
        merge_auth_profile_state,
    )
    merged = {
        **store,
        **merge_auth_profile_state(
            coerce_auth_profile_state(raw),
            load_persisted_auth_profile_state(agent_dir, database),
        ),
    }
    return merged
