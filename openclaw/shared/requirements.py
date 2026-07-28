"""Requirement types describe runtime requirements advertised by shared surfaces."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable


@dataclass
class Requirements:
    bins: list[str] = field(default_factory=list)
    any_bins: list[str] = field(default_factory=list)
    env: list[str] = field(default_factory=list)
    config: list[str] = field(default_factory=list)
    os: list[str] = field(default_factory=list)


@dataclass
class RequirementConfigCheck:
    path: str
    satisfied: bool


@dataclass
class RequirementsMetadata:
    bins: list[str] | None = None
    any_bins: list[str] | None = None
    env: list[str] | None = None
    config: list[str] | None = None
    os: list[str] | None = None


@dataclass
class RequirementRemote:
    has_bin: Callable[[str], bool] | None = None
    has_any_bin: Callable[[list[str]], bool] | None = None
    platforms: list[str] | None = None


def _normalize_os_requirement_platform(platform_name: str) -> str:
    normalized = platform_name.strip().lower()
    return "darwin" if normalized == "macos" else normalized


def resolve_missing_bins(
    required: list[str],
    has_local_bin: Callable[[str], bool],
    has_remote_bin: Callable[[str], bool] | None = None,
) -> list[str]:
    result: list[str] = []
    for bin_name in required:
        if has_local_bin(bin_name):
            continue
        if has_remote_bin and has_remote_bin(bin_name):
            continue
        result.append(bin_name)
    return result


def resolve_missing_any_bins(
    required: list[str],
    has_local_bin: Callable[[str], bool],
    has_remote_any_bin: Callable[[list[str]], bool] | None = None,
) -> list[str]:
    if len(required) == 0:
        return []
    if any(has_local_bin(bin) for bin in required):
        return []
    if has_remote_any_bin and has_remote_any_bin(required):
        return []
    return list(required)


def resolve_missing_os(
    required: list[str],
    local_platform: str,
    remote_platforms: list[str] | None = None,
) -> list[str]:
    if len(required) == 0:
        return []
    local = _normalize_os_requirement_platform(local_platform)
    required_set = {_normalize_os_requirement_platform(p) for p in required}
    if local in required_set:
        return []
    if remote_platforms:
        for platform in remote_platforms:
            if _normalize_os_requirement_platform(platform) in required_set:
                return []
    return list(required)


def resolve_missing_env(
    required: list[str],
    is_satisfied: Callable[[str], bool],
) -> list[str]:
    missing: list[str] = []
    for env_name in required:
        if is_satisfied(env_name):
            continue
        missing.append(env_name)
    return missing


def build_config_checks(
    required: list[str],
    is_satisfied: Callable[[str], bool],
) -> list[RequirementConfigCheck]:
    return [RequirementConfigCheck(path=path, satisfied=is_satisfied(path)) for path in required]


def evaluate_requirements(
    always: bool,
    required: Requirements,
    has_local_bin: Callable[[str], bool],
    local_platform: str,
    is_env_satisfied: Callable[[str], bool],
    is_config_satisfied: Callable[[str], bool],
    has_remote_bin: Callable[[str], bool] | None = None,
    has_remote_any_bin: Callable[[list[str]], bool] | None = None,
    remote_platforms: list[str] | None = None,
) -> tuple[Requirements, bool, list[RequirementConfigCheck]]:
    missing_bins = resolve_missing_bins(required.bins, has_local_bin, has_remote_bin)
    missing_any_bins = resolve_missing_any_bins(required.any_bins, has_local_bin, has_remote_any_bin)
    missing_os = resolve_missing_os(required.os, local_platform, remote_platforms)
    missing_env = resolve_missing_env(required.env, is_env_satisfied)
    config_checks = build_config_checks(required.config, is_config_satisfied)
    missing_config = [check.path for check in config_checks if not check.satisfied]

    if always:
        missing = Requirements()
    else:
        missing = Requirements(
            bins=missing_bins,
            any_bins=missing_any_bins,
            env=missing_env,
            config=missing_config,
            os=missing_os,
        )

    eligible = always or (
        len(missing.bins) == 0
        and len(missing.any_bins) == 0
        and len(missing.env) == 0
        and len(missing.config) == 0
        and len(missing.os) == 0
    )

    return missing, eligible, config_checks


def evaluate_requirements_from_metadata(
    always: bool,
    metadata: RequirementsMetadata | None,
    has_local_bin: Callable[[str], bool],
    local_platform: str,
    is_env_satisfied: Callable[[str], bool],
    is_config_satisfied: Callable[[str], bool],
    has_remote_bin: Callable[[str], bool] | None = None,
    has_remote_any_bin: Callable[[list[str]], bool] | None = None,
    remote_platforms: list[str] | None = None,
) -> tuple[Requirements, Requirements, bool, list[RequirementConfigCheck]]:
    required = Requirements(
        bins=metadata.bins if metadata and metadata.bins else [],
        any_bins=metadata.any_bins if metadata and metadata.any_bins else [],
        env=metadata.env if metadata and metadata.env else [],
        config=metadata.config if metadata and metadata.config else [],
        os=metadata.os if metadata and metadata.os else [],
    )
    missing, eligible, config_checks = evaluate_requirements(
        always=always,
        required=required,
        has_local_bin=has_local_bin,
        local_platform=local_platform,
        is_env_satisfied=is_env_satisfied,
        is_config_satisfied=is_config_satisfied,
        has_remote_bin=has_remote_bin,
        has_remote_any_bin=has_remote_any_bin,
        remote_platforms=remote_platforms,
    )
    return required, missing, eligible, config_checks


def evaluate_requirements_from_metadata_with_remote(
    always: bool,
    metadata: RequirementsMetadata | None,
    has_local_bin: Callable[[str], bool],
    local_platform: str,
    is_env_satisfied: Callable[[str], bool],
    is_config_satisfied: Callable[[str], bool],
    remote: RequirementRemote | None = None,
) -> tuple[Requirements, Requirements, bool, list[RequirementConfigCheck]]:
    return evaluate_requirements_from_metadata(
        always=always,
        metadata=metadata,
        has_local_bin=has_local_bin,
        local_platform=local_platform,
        is_env_satisfied=is_env_satisfied,
        is_config_satisfied=is_config_satisfied,
        has_remote_bin=remote.has_bin if remote else None,
        has_remote_any_bin=remote.has_any_bin if remote else None,
        remote_platforms=remote.platforms if remote else None,
    )
