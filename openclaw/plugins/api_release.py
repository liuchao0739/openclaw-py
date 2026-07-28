from __future__ import annotations

from typing import Any

from openclaw.plugins.constants import (
    EXPERIMENTAL_PLUGIN_APIS,
    BETA_PLUGIN_APIS,
    STABLE_PLUGIN_APIS,
)


def resolve_api_release_level(api_id: str) -> str:
    if api_id in STABLE_PLUGIN_APIS:
        return "stable"
    if api_id in BETA_PLUGIN_APIS:
        return "beta"
    if api_id in EXPERIMENTAL_PLUGIN_APIS:
        return "experimental"
    return "unknown"


def is_api_stable(api_id: str) -> bool:
    return resolve_api_release_level(api_id) == "stable"


def is_api_beta(api_id: str) -> bool:
    return resolve_api_release_level(api_id) == "beta"


def is_api_experimental(api_id: str) -> bool:
    return resolve_api_release_level(api_id) == "experimental"


def list_stable_apis() -> set[str]:
    return set(STABLE_PLUGIN_APIS)


def list_beta_apis() -> set[str]:
    return set(BETA_PLUGIN_APIS)


def list_experimental_apis() -> set[str]:
    return set(EXPERIMENTAL_PLUGIN_APIS)
