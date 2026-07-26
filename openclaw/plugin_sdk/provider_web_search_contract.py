"""Public contract-safe web-search registration helpers for provider plugins."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, TypedDict

from openclaw.plugin_sdk.provider_enable_config import enable_plugin_in_config


class CreateWebSearchProviderContractFieldsOptions(TypedDict, total=False):
    credential_path: str
    inactive_secret_paths: list[str]
    search_credential: dict[str, Any]
    configured_credential: dict[str, Any]
    selection_plugin_id: str


def _get_scoped_credential_value(
    search_config: dict[str, Any] | None,
    key: str,
) -> Any:
    if not search_config:
        return None
    scoped = search_config.get(key)
    if not isinstance(scoped, dict):
        return None
    return scoped.get("apiKey")


def _set_scoped_credential_value(
    search_config_target: dict[str, Any],
    key: str,
    value: Any,
) -> None:
    scoped = search_config_target.get(key)
    if not isinstance(scoped, dict):
        search_config_target[key] = {"apiKey": value}
        return
    scoped["apiKey"] = value


def _create_search_credential_fields(
    credential: dict[str, Any],
) -> dict[str, Callable[..., Any]]:
    credential_type = credential.get("type")
    if credential_type == "scoped":
        scope_id = str(credential.get("scopeId") or credential.get("scope_id") or "")

        def get_credential_value(search_config: dict[str, Any] | None = None) -> Any:
            return _get_scoped_credential_value(search_config, scope_id)

        def set_credential_value(search_config_target: dict[str, Any], value: Any) -> None:
            _set_scoped_credential_value(search_config_target, scope_id, value)

        return {
            "get_credential_value": get_credential_value,
            "set_credential_value": set_credential_value,
        }
    if credential_type == "top-level":

        def get_top_level(search_config: dict[str, Any] | None = None) -> Any:
            return search_config.get("apiKey") if search_config else None

        def set_top_level(search_config_target: dict[str, Any], value: Any) -> None:
            search_config_target["apiKey"] = value

        return {
            "get_credential_value": get_top_level,
            "set_credential_value": set_top_level,
        }
    if credential_type == "none":

        def get_none(_search_config: dict[str, Any] | None = None) -> Any:
            return None

        def set_none(_search_config_target: dict[str, Any], _value: Any) -> None:
            return None

        return {
            "get_credential_value": get_none,
            "set_credential_value": set_none,
        }
    raise ValueError("Unsupported web search credential type")


def create_web_search_provider_contract_fields(
    options: CreateWebSearchProviderContractFieldsOptions,
) -> dict[str, Any]:
    """Build the public web-search provider hooks, including optional selection-time enabling."""
    credential_path = options.get("credential_path", "")
    inactive_secret_paths = options.get("inactive_secret_paths")
    if inactive_secret_paths is None:
        inactive_secret_paths = [credential_path] if credential_path else []

    fields: dict[str, Any] = {
        "inactive_secret_paths": inactive_secret_paths,
        **_create_search_credential_fields(options["search_credential"]),
    }

    selection_plugin_id = options.get("selection_plugin_id")
    if selection_plugin_id:

        def apply_selection_config(config: dict[str, Any]) -> dict[str, Any]:
            return enable_plugin_in_config(config, selection_plugin_id)["config"]

        fields["apply_selection_config"] = apply_selection_config

    return fields
