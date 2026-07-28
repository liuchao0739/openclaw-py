from __future__ import annotations

from typing import Any

from openclaw.packages.normalization_core import (
    is_record,
    normalize_lowercase_string_or_empty,
)
from openclaw.plugin_sdk.provider_auth import CLAUDE_CLI_PROFILE_ID

from .claude_model_refs import resolve_claude_cli_anthropic_model_refs
from .cli_auth_seam import (
    read_claude_cli_credentials_for_setup,
    read_claude_cli_credentials_for_setup_non_interactive,
)
from .cli_constants import CLAUDE_CLI_BACKEND_ID
from .cli_shared import CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS


def _to_anthropic_model_ref(raw: str) -> str | None:
    result = resolve_claude_cli_anthropic_model_refs(raw)
    return result.get("rewriteRef") if result else None


def _to_anthropic_runtime_refs(raw: str) -> list[str]:
    result = resolve_claude_cli_anthropic_model_refs(raw)
    return result.get("runtimeRefs", []) if result else []


def _to_anthropic_selected_model_ref(raw: str) -> str | None:
    result = resolve_claude_cli_anthropic_model_refs(raw)
    if not result:
        return None
    return result.get("rewriteRef") or result.get("selectedRef")


def _rewrite_model_selection(model: Any) -> dict[str, Any]:
    if isinstance(model, str):
        runtime_refs = _to_anthropic_runtime_refs(model)
        converted = _to_anthropic_model_ref(model)
        selected_ref = converted or _to_anthropic_selected_model_ref(model)
        if converted:
            return {
                "value": converted,
                "primary": converted,
                "runtimeRefs": runtime_refs,
                "changed": True,
            }
        result: dict[str, Any] = {
            "value": model,
            "runtimeRefs": runtime_refs,
            "changed": False,
        }
        if selected_ref:
            result["primary"] = selected_ref
        return result
    if not model or not isinstance(model, dict):
        return {"value": model, "runtimeRefs": [], "changed": False}

    current = dict(model)
    next_dict: dict[str, Any] = dict(current)
    runtime_refs: list[str] = []
    changed = False
    primary: str | None = None

    if isinstance(current.get("primary"), str):
        runtime_refs.extend(_to_anthropic_runtime_refs(current["primary"]))
        converted = _to_anthropic_model_ref(current["primary"])
        if converted:
            next_dict["primary"] = converted
            primary = converted
            changed = True
        else:
            primary = _to_anthropic_selected_model_ref(current["primary"])

    current_fallbacks = current.get("fallbacks")
    if isinstance(current_fallbacks, list):
        next_fallbacks = []
        for entry in current_fallbacks:
            if not isinstance(entry, str):
                next_fallbacks.append(entry)
                continue
            runtime_refs.extend(_to_anthropic_runtime_refs(entry))
            converted = _to_anthropic_model_ref(entry)
            next_fallbacks.append(converted or entry)
        if next_fallbacks != current_fallbacks:
            next_dict["fallbacks"] = next_fallbacks
            changed = True

    result: dict[str, Any] = {
        "value": next_dict if changed else model,
        "runtimeRefs": runtime_refs,
        "changed": changed,
    }
    if primary:
        result["primary"] = primary
    return result


def _rewrite_model_entry_map(
    models: dict[str, Any] | None,
) -> dict[str, Any]:
    if not isinstance(models, dict):
        return {"value": models, "migrated": [], "runtimeRefs": []}

    next_dict = dict(models)
    migrated: list[str] = []
    runtime_refs: list[str] = []

    for raw_key, value in models.items():
        runtime_refs.extend(_to_anthropic_runtime_refs(raw_key))
        converted = _to_anthropic_model_ref(raw_key)
        if not converted:
            continue
        if converted == raw_key:
            continue
        if converted not in next_dict:
            next_dict[converted] = value
        if normalize_lowercase_string_or_empty(raw_key).startswith(
            f"{CLAUDE_CLI_BACKEND_ID}/"
        ):
            del next_dict[raw_key]
        migrated.append(converted)

    return {
        "value": next_dict if migrated or runtime_refs else models,
        "migrated": migrated,
        "runtimeRefs": runtime_refs,
    }


def _seed_claude_cli_allowlist(
    models: dict[str, Any],
    selected_refs: list[str] | None = None,
) -> dict[str, Any]:
    next_dict = dict(models)
    runtime_refs: set[str] = set()
    for ref in CLAUDE_CLI_DEFAULT_ALLOWLIST_REFS:
        canonical_ref = _to_anthropic_model_ref(ref) or ref
        runtime_refs.add(canonical_ref)
    if selected_refs:
        for ref in selected_refs:
            runtime_refs.add(ref)
    for ref in runtime_refs:
        next_dict[ref] = _model_entry_with_claude_cli_runtime(next_dict.get(ref))
    return next_dict


def _model_entry_with_claude_cli_runtime(entry: Any) -> dict[str, Any]:
    base: dict[str, Any] = dict(entry) if is_record(entry) else {}
    current_runtime_id = None
    agent_runtime = base.get("agentRuntime")
    if is_record(agent_runtime):
        current_runtime_id = agent_runtime.get("id")
    current_runtime = (
        normalize_lowercase_string_or_empty(current_runtime_id)
        if isinstance(current_runtime_id, str)
        else ""
    )
    if current_runtime and current_runtime != "auto":
        return base
    ar = base.get("agentRuntime", {})
    if not is_record(ar):
        ar = {}
    ar = {**ar, "id": CLAUDE_CLI_BACKEND_ID}
    base["agentRuntime"] = ar
    return base


def _build_claude_cli_auth_profiles(
    credential: dict[str, Any] | None,
) -> list[dict[str, Any]]:
    if not credential:
        return []
    if credential.get("type") == "oauth":
        return [
            {
                "profileId": CLAUDE_CLI_PROFILE_ID,
                "credential": {
                    "type": "oauth",
                    "provider": CLAUDE_CLI_BACKEND_ID,
                    "access": credential.get("access"),
                    "refresh": credential.get("refresh"),
                    "expires": credential.get("expires"),
                },
            }
        ]
    return [
        {
            "profileId": CLAUDE_CLI_PROFILE_ID,
            "credential": {
                "type": "token",
                "provider": CLAUDE_CLI_BACKEND_ID,
                "token": credential.get("token"),
                "expires": credential.get("expires"),
            },
        }
    ]


def build_anthropic_cli_migration_result(
    config: dict[str, Any],
    credential: dict[str, Any] | None = None,
) -> dict[str, Any]:
    defaults = config.get("agents", {}).get("defaults", {})
    if not isinstance(defaults, dict):
        defaults = {}
    rewritten_model = _rewrite_model_selection(defaults.get("model"))
    rewritten_models = _rewrite_model_entry_map(defaults.get("models"))
    existing_models = rewritten_models.get("value") or defaults.get("models") or {}
    if not isinstance(existing_models, dict):
        existing_models = {}
    next_models = _seed_claude_cli_allowlist(
        existing_models,
        [
            *rewritten_model.get("runtimeRefs", []),
            *rewritten_models.get("runtimeRefs", []),
            *rewritten_models.get("migrated", []),
        ],
    )
    default_model = rewritten_model.get("primary") or "anthropic/claude-opus-4-8"

    result: dict[str, Any] = {
        "profiles": _build_claude_cli_auth_profiles(credential),
        "configPatch": {
            "agents": {
                "defaults": {
                    **(
                        {"model": rewritten_model["value"]}
                        if rewritten_model.get("changed")
                        else {}
                    ),
                    "models": next_models,
                },
            },
        },
        "replaceDefaultModels": True,
        "defaultModel": default_model,
        "notes": [
            "Claude CLI auth detected; kept Anthropic model refs and selected the local Claude CLI runtime.",
            "Existing Anthropic auth profiles are kept for rollback.",
        ],
    }
    migrated = rewritten_models.get("migrated", [])
    if migrated:
        result["notes"].append(f"Migrated allowlist entries: {', '.join(migrated)}.")
    return result