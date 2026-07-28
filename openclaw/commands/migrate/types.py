from __future__ import annotations

from typing import Any, TypedDict


class MigrateApplyOptions(TypedDict, total=False):
    provider: str
    source: str | None
    includeSecrets: bool
    overwrite: bool
    providerOptions: dict[str, Any] | None
    backupPath: str | None
    backupOutput: str | None
    yes: bool
    noBackup: bool
    json: bool
