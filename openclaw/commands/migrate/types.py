"""Shared option types for the migrate command family."""

from __future__ import annotations

from typing import Any, TypedDict


class MigrateCommonOptions(TypedDict, total=False):
    provider: str
    source: str
    includeSecrets: bool
    authCredentials: bool
    overwrite: bool
    skills: list[str]
    plugins: list[str]
    verifyPluginApps: bool
    json: bool
    suppressPlanLog: bool
    configOverride: dict[str, Any]
    configPatchMode: str  # "return"


class MigrateApplyOptions(MigrateCommonOptions, total=False):
    yes: bool
    noBackup: bool
    force: bool
    backupOutput: str
    preflightPlan: Any


class MigrateDefaultOptions(MigrateApplyOptions, total=False):
    dryRun: bool
