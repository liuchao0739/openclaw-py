from __future__ import annotations

from typing import Any, Literal

from openclaw.infra.clawhub_spec import parse_clawhub_plugin_spec
from openclaw.infra.npm_registry_spec import parse_registry_npm_spec
from openclaw.infra.prototype_keys import is_blocked_object_key
from openclaw_packages.model_catalog_core.model_catalog_normalize import (
    normalize_model_catalog,
)
from openclaw_packages.model_catalog_core.model_catalog_refs import (
    normalize_model_catalog_provider_id,
)
from openclaw_packages.model_catalog_core.model_catalog_types import ModelCatalogProvider
from openclaw_packages.normalization_core import (
    as_finite_number,
    is_record,
    normalize_optional_string,
    normalize_unique_trimmed_string_list,
)

from .types import (
    OpenClawProviderIndex,
    OpenClawProviderIndexPlugin,
    OpenClawProviderIndexPluginInstall,
    OpenClawProviderIndexProvider,
    OpenClawProviderIndexProviderAuthChoice,
)

_OPENCLAW_PROVIDER_INDEX_VERSION = 1

_ONBOARDING_SCOPES = frozenset({"text-inference", "image-generation", "music-generation"})
_ASSISTANT_VISIBILITIES = frozenset({"visible", "manual-only"})


def _normalize_safe_key(value: Any) -> str:
    key = normalize_optional_string(value) or ""
    return key if key and not is_blocked_object_key(key) else ""


def _normalize_install(value: Any) -> OpenClawProviderIndexPluginInstall | None:
    if not is_record(value):
        return None
    clawhub_spec = normalize_optional_string(value.get("clawhubSpec"))
    parsed_clawhub = parse_clawhub_plugin_spec(clawhub_spec) if clawhub_spec else None
    npm_spec = normalize_optional_string(value.get("npmSpec"))
    parsed_npm = parse_registry_npm_spec(npm_spec) if npm_spec else None
    if not parsed_clawhub and not parsed_npm:
        return None
    install: OpenClawProviderIndexPluginInstall = {}
    if parsed_clawhub:
        install["clawhubSpec"] = clawhub_spec
    if parsed_npm:
        install["npmSpec"] = parsed_npm["raw"]
    default_choice_value = normalize_optional_string(value.get("defaultChoice"))
    if default_choice_value == "clawhub" and parsed_clawhub:
        install["defaultChoice"] = "clawhub"
    elif default_choice_value == "npm" and parsed_npm:
        install["defaultChoice"] = "npm"
    min_host_version = normalize_optional_string(value.get("minHostVersion"))
    if min_host_version:
        install["minHostVersion"] = min_host_version
    expected_integrity = normalize_optional_string(value.get("expectedIntegrity"))
    if expected_integrity:
        install["expectedIntegrity"] = expected_integrity
    return install


def _normalize_plugin(value: Any) -> OpenClawProviderIndexPlugin | None:
    if not is_record(value):
        return None
    plugin_id = _normalize_safe_key(value.get("id"))
    if not plugin_id:
        return None
    package_name = normalize_optional_string(value.get("package")) or ""
    source = normalize_optional_string(value.get("source")) or ""
    install = _normalize_install(value.get("install"))
    plugin: OpenClawProviderIndexPlugin = {"id": plugin_id}
    if package_name:
        plugin["package"] = package_name
    if source:
        plugin["source"] = source
    if install:
        plugin["install"] = install
    return plugin


def _normalize_categories(value: Any) -> list[str]:
    return normalize_unique_trimmed_string_list(value)


def _normalize_preview_catalog(
    provider_id: str,
    value: Any,
) -> ModelCatalogProvider | None:
    catalog = normalize_model_catalog(
        {"providers": {provider_id: value}},
        owned_providers={provider_id},
    )
    if catalog is None:
        return None
    provider = catalog.get("providers", {}).get(provider_id)
    if provider is None:
        return None
    for model in provider.get("models", []):
        if model.get("status") is None:
            model["status"] = "preview"
    return provider


def _normalize_onboarding_scopes(
    value: Any,
) -> list[Literal["text-inference", "image-generation", "music-generation"]] | None:
    scopes = [
        scope
        for scope in normalize_unique_trimmed_string_list(value)
        if scope in _ONBOARDING_SCOPES
    ]
    return scopes if scopes else None


def _normalize_assistant_visibility(
    value: Any,
) -> Literal["visible", "manual-only"] | None:
    return value if value in _ASSISTANT_VISIBILITIES else None


def _normalize_auth_choice(
    provider_id: str,
    provider_name: str,
    value: Any,
) -> OpenClawProviderIndexProviderAuthChoice | None:
    if not is_record(value):
        return None
    method = _normalize_safe_key(value.get("method"))
    choice_id = _normalize_safe_key(value.get("choiceId"))
    choice_label = normalize_optional_string(value.get("choiceLabel")) or ""
    if not method or not choice_id or not choice_label:
        return None
    choice: OpenClawProviderIndexProviderAuthChoice = {
        "method": method,
        "choiceId": choice_id,
        "choiceLabel": choice_label,
    }
    choice_hint = normalize_optional_string(value.get("choiceHint"))
    if choice_hint:
        choice["choiceHint"] = choice_hint
    assistant_priority = as_finite_number(value.get("assistantPriority"))
    if assistant_priority is not None:
        choice["assistantPriority"] = assistant_priority
    assistant_visibility = _normalize_assistant_visibility(value.get("assistantVisibility"))
    if assistant_visibility is not None:
        choice["assistantVisibility"] = assistant_visibility
    group_id = _normalize_safe_key(value.get("groupId")) or provider_id
    choice["groupId"] = group_id
    group_label = normalize_optional_string(value.get("groupLabel")) or provider_name
    choice["groupLabel"] = group_label
    group_hint = normalize_optional_string(value.get("groupHint"))
    if group_hint:
        choice["groupHint"] = group_hint
    option_key = _normalize_safe_key(value.get("optionKey"))
    if option_key:
        choice["optionKey"] = option_key
    cli_flag = normalize_optional_string(value.get("cliFlag"))
    if cli_flag:
        choice["cliFlag"] = cli_flag
    cli_option = normalize_optional_string(value.get("cliOption"))
    if cli_option:
        choice["cliOption"] = cli_option
    cli_description = normalize_optional_string(value.get("cliDescription"))
    if cli_description:
        choice["cliDescription"] = cli_description
    onboarding_scopes = _normalize_onboarding_scopes(value.get("onboardingScopes"))
    if onboarding_scopes:
        choice["onboardingScopes"] = onboarding_scopes
    return choice


def _normalize_auth_choices(
    provider_id: str,
    provider_name: str,
    value: Any,
) -> list[OpenClawProviderIndexProviderAuthChoice] | None:
    if not isinstance(value, list):
        return None
    choices = [
        choice
        for item in value
        if (choice := _normalize_auth_choice(provider_id, provider_name, item)) is not None
    ]
    return choices if choices else None


def _normalize_provider(
    raw_provider_id: str,
    value: Any,
) -> OpenClawProviderIndexProvider | None:
    if not is_record(value):
        return None
    provider_id = normalize_model_catalog_provider_id(raw_provider_id)
    if not provider_id:
        return None
    id_value = normalize_model_catalog_provider_id(
        normalize_optional_string(value.get("id")) or ""
    )
    if id_value and id_value != provider_id:
        return None
    name = normalize_optional_string(value.get("name")) or ""
    plugin = _normalize_plugin(value.get("plugin"))
    if not name or plugin is None:
        return None
    provider: OpenClawProviderIndexProvider = {
        "id": provider_id,
        "name": name,
        "plugin": plugin,
    }
    docs = normalize_optional_string(value.get("docs")) or ""
    if docs:
        provider["docs"] = docs
    categories = _normalize_categories(value.get("categories"))
    if categories:
        provider["categories"] = categories
    auth_choices = _normalize_auth_choices(provider_id, name, value.get("authChoices"))
    if auth_choices:
        provider["authChoices"] = auth_choices
    preview_catalog = _normalize_preview_catalog(provider_id, value.get("previewCatalog"))
    if preview_catalog:
        provider["previewCatalog"] = preview_catalog
    return provider


def normalize_openclaw_provider_index(value: Any) -> OpenClawProviderIndex | None:
    if not is_record(value) or value.get("version") != _OPENCLAW_PROVIDER_INDEX_VERSION:
        return None
    if not is_record(value.get("providers")):
        return None
    providers: dict[str, OpenClawProviderIndexProvider] = {}
    for raw_provider_id, raw_provider in value["providers"].items():
        provider_id = normalize_model_catalog_provider_id(str(raw_provider_id))
        if not provider_id or is_blocked_object_key(provider_id):
            continue
        provider = _normalize_provider(provider_id, raw_provider)
        if provider is not None:
            providers[provider_id] = provider
    sorted_providers = dict(
        sorted(providers.items(), key=lambda item: item[0])
    )
    return {
        "version": _OPENCLAW_PROVIDER_INDEX_VERSION,
        "providers": sorted_providers,
    }


__all__ = [
    "normalize_openclaw_provider_index",
]
