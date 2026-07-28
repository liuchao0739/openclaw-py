from __future__ import annotations

import json
import os
from typing import Any

from openclaw.agents.auth_profiles.constants import AUTH_STORE_VERSION, log
from openclaw.agents.auth_profiles.path_constants import (
    AUTH_PROFILE_FILENAME,
    AUTH_STATE_FILENAME,
    LEGACY_AUTH_FILENAME,
)
from openclaw.agents.auth_profiles.types import (
    AuthProfileSecretsStore,
    AuthProfileState,
    AuthProfileStateStore,
    AuthProfileStore,
)


_runtime_auth_profile_store_snapshots: dict[str | None, AuthProfileStore] = {}
_runtime_external_profile_ids_authoritative: set[str] = set()


def get_runtime_auth_profile_store_snapshot(
    agent_dir: str | None = None,
) -> AuthProfileStore | None:
    return _runtime_auth_profile_store_snapshots.get(agent_dir)


def has_any_runtime_auth_profile_store_source(
    agent_dir: str | None = None,
) -> bool:
    snapshot = _runtime_auth_profile_store_snapshots.get(agent_dir)
    if snapshot and snapshot.get("profiles"):
        return True
    return False


def set_runtime_auth_profile_store_snapshot(
    store: AuthProfileStore,
    agent_dir: str | None = None,
) -> None:
    _runtime_auth_profile_store_snapshots[agent_dir] = store


def clear_runtime_auth_profile_store_snapshots() -> None:
    _runtime_auth_profile_store_snapshots.clear()


def replace_runtime_auth_profile_store_snapshots(
    entries: list[dict[str, Any]],
) -> None:
    _runtime_auth_profile_store_snapshots.clear()
    for entry in entries:
        agent_dir = entry.get("agentDir")
        store = entry.get("store")
        if store:
            _runtime_auth_profile_store_snapshots[agent_dir] = store


def resolve_auth_store_path(state_dir: str = ".openclaw") -> str:
    return os.path.join(state_dir, AUTH_PROFILE_FILENAME)


def resolve_auth_state_path(state_dir: str = ".openclaw") -> str:
    return os.path.join(state_dir, AUTH_STATE_FILENAME)


def resolve_legacy_auth_store_path(state_dir: str = ".openclaw") -> str:
    return os.path.join(state_dir, LEGACY_AUTH_FILENAME)


def has_any_auth_profile_store_source(agent_dir: str | None = None) -> bool:
    if has_local_auth_profile_store_source(agent_dir):
        return True
    if has_any_runtime_auth_profile_store_source(agent_dir):
        return True
    return False


def has_local_auth_profile_store_source(agent_dir: str | None = None) -> bool:
    runtime_store = get_runtime_auth_profile_store_snapshot(agent_dir)
    if runtime_store and runtime_store.get("profiles"):
        return True

    state_dir = agent_dir or ".openclaw"
    for filename in (AUTH_PROFILE_FILENAME, AUTH_STATE_FILENAME, LEGACY_AUTH_FILENAME):
        if os.path.exists(os.path.join(state_dir, filename)):
            return True
    return False


def _read_legacy_oauth_file() -> dict[str, Any] | None:
    from openclaw.config.paths import resolve_oauth_path
    oauth_path = resolve_oauth_path()
    if not os.path.exists(oauth_path):
        return None
    try:
        with open(oauth_path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return None


def merge_oauth_file_into_store(store: AuthProfileStore) -> bool:
    oauth_raw = _read_legacy_oauth_file()
    if not oauth_raw:
        return False
    mutated = False
    for provider, creds in oauth_raw.items():
        if not isinstance(creds, dict):
            continue
        profile_id = f"{provider}:default"
        if profile_id in store.get("profiles", {}):
            continue
        store.setdefault("profiles", {})[profile_id] = {
            "type": "oauth",
            "provider": provider,
            **creds,
        }
        mutated = True
    return mutated


def build_local_auth_profile_store_for_save(
    store: AuthProfileStore,
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    from openclaw.agents.auth_profiles.clone import clone_auth_profile_store
    local_store = clone_auth_profile_store(store)
    external_profiles_cache: list[dict[str, Any]] | None = None

    profiles_to_keep: dict[str, Any] = {}
    for profile_id, credential in local_store.get("profiles", {}).items():
        if credential.get("type") != "oauth":
            profiles_to_keep[profile_id] = credential
            continue
        profiles_to_keep[profile_id] = credential

    local_store["profiles"] = profiles_to_keep
    return local_store


def build_persisted_auth_profile_secrets_store(
    store: AuthProfileStore,
    should_persist_profile: Any = None,
) -> AuthProfileSecretsStore:
    profiles: dict[str, Any] = {}
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


def load_auth_profile_store() -> AuthProfileStore:
    from openclaw.agents.auth_profiles.persisted import load_persisted_auth_profile_store
    store = load_persisted_auth_profile_store()
    if store:
        return store
    return {"version": AUTH_STORE_VERSION, "profiles": {}}


def load_auth_profile_store_for_agent(
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    from openclaw.agents.auth_profiles.persisted import load_persisted_auth_profile_store
    store = load_persisted_auth_profile_store(agent_dir)
    if store:
        return store
    return {"version": AUTH_STORE_VERSION, "profiles": {}}


def load_auth_profile_store_for_runtime(
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    return load_auth_profile_store_for_agent(agent_dir, options)


def ensure_auth_profile_store(
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    return load_auth_profile_store_for_runtime(agent_dir, options)


def save_auth_profile_store(
    store: AuthProfileStore,
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
    database: Any = None,
) -> None:
    from openclaw.agents.auth_profiles.sqlite import (
        write_persisted_auth_profile_store_raw,
    )
    from openclaw.agents.auth_profiles.state import (
        build_persisted_auth_profile_state,
        save_persisted_auth_profile_state,
    )
    from openclaw.agents.auth_profiles.persisted import (
        build_persisted_auth_profile_secrets_store,
    )

    local_store = build_local_auth_profile_store_for_save(
        store, agent_dir, options
    )
    payload = build_persisted_auth_profile_secrets_store(local_store)
    write_persisted_auth_profile_store_raw(payload, agent_dir, database)

    state_payload = build_persisted_auth_profile_state(local_store)
    if database:
        from openclaw.agents.auth_profiles.sqlite import (
            write_persisted_auth_profile_state_raw,
        )
        write_persisted_auth_profile_state_raw(state_payload, agent_dir, database)
    else:
        save_persisted_auth_profile_state(local_store, agent_dir)

    set_runtime_auth_profile_store_snapshot(store, agent_dir)


def update_auth_profile_store_with_lock(
    agent_dir: str | None = None,
    save_options: dict[str, Any] | None = None,
    updater: Any = None,
) -> AuthProfileStore | None:
    try:
        store = load_auth_profile_store_for_agent(agent_dir, {"readOnly": True})
        should_save = updater(store) if updater else False
        if should_save:
            save_auth_profile_store(store, agent_dir, save_options)
        return store
    except Exception:
        return None


def load_auth_profile_store_for_secrets_runtime(
    agent_dir: str | None = None,
    options: dict[str, Any] | None = None,
) -> AuthProfileStore:
    return load_auth_profile_store_for_runtime(agent_dir, {
        **(options or {}),
        "readOnly": True,
        "allowKeychainPrompt": False,
    })
