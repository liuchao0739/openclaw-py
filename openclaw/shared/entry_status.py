"""Entry status helpers resolve display metadata for run and queue entries."""

from __future__ import annotations

from typing import Any, Callable

from .entry_metadata import resolve_emoji_and_homepage
from .requirements import (
    Requirements,
    RequirementConfigCheck,
    RequirementRemote,
    evaluate_requirements_from_metadata_with_remote,
)


def evaluate_entry_metadata_requirements(
    always: bool,
    metadata: dict[str, Any] | None = None,
    frontmatter: dict[str, Any] | None = None,
    has_local_bin: Callable[[str], bool] = None,
    local_platform: str = "",
    remote: RequirementRemote | None = None,
    is_env_satisfied: Callable[[str], bool] = None,
    is_config_satisfied: Callable[[str], bool] = None,
) -> dict[str, Any]:
    emoji, homepage = resolve_emoji_and_homepage(metadata, frontmatter)
    required, missing, eligible, config_checks = evaluate_requirements_from_metadata_with_remote(
        always=always,
        metadata=metadata,
        has_local_bin=has_local_bin,
        local_platform=local_platform,
        is_env_satisfied=is_env_satisfied,
        is_config_satisfied=is_config_satisfied,
        remote=remote,
    )
    result: dict[str, Any] = {
        "required": required,
        "missing": missing,
        "requirementsSatisfied": eligible,
        "configChecks": config_checks,
    }
    if emoji:
        result["emoji"] = emoji
    if homepage:
        result["homepage"] = homepage
    return result


def evaluate_entry_metadata_requirements_for_current_platform(
    always: bool,
    metadata: dict[str, Any] | None = None,
    frontmatter: dict[str, Any] | None = None,
    has_local_bin: Callable[[str], bool] = None,
    remote: RequirementRemote | None = None,
    is_env_satisfied: Callable[[str], bool] = None,
    is_config_satisfied: Callable[[str], bool] = None,
) -> dict[str, Any]:
    import platform
    return evaluate_entry_metadata_requirements(
        always=always,
        metadata=metadata,
        frontmatter=frontmatter,
        has_local_bin=has_local_bin,
        local_platform=platform.system().lower(),
        remote=remote,
        is_env_satisfied=is_env_satisfied,
        is_config_satisfied=is_config_satisfied,
    )


def evaluate_entry_requirements_for_current_platform(
    always: bool,
    entry: dict[str, Any],
    has_local_bin: Callable[[str], bool] = None,
    remote: RequirementRemote | None = None,
    is_env_satisfied: Callable[[str], bool] = None,
    is_config_satisfied: Callable[[str], bool] = None,
) -> dict[str, Any]:
    return evaluate_entry_metadata_requirements_for_current_platform(
        always=always,
        metadata=entry.get("metadata"),
        frontmatter=entry.get("frontmatter"),
        has_local_bin=has_local_bin,
        remote=remote,
        is_env_satisfied=is_env_satisfied,
        is_config_satisfied=is_config_satisfied,
    )
