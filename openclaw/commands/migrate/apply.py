from __future__ import annotations

import json
import os
import shutil
from typing import Any

from openclaw.commands.migrate.context import build_migration_context, create_migration_logger
from openclaw.commands.migrate.types import MigrateApplyOptions


def _backup_file(src: str, dst_dir: str) -> str | None:
    if not os.path.exists(src):
        return None
    os.makedirs(dst_dir, exist_ok=True)
    basename = os.path.basename(src)
    dst = os.path.join(dst_dir, basename)
    shutil.copy2(src, dst)
    return dst


def _write_config(path: str, config: dict[str, Any]) -> None:
    os.makedirs(os.path.dirname(path) if os.path.dirname(path) else ".", exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


async def migrate_apply(
    opts: MigrateApplyOptions,
    runtime: dict[str, Any] | None = None,
) -> dict[str, Any]:
    rt = runtime or {}
    logger = create_migration_logger(rt, opts.get("json", False))

    context = build_migration_context(
        source=opts.get("source"),
        include_secrets=opts.get("includeSecrets", False),
        overwrite=opts.get("overwrite", False),
        provider_options=opts.get("providerOptions"),
        backup_path=opts.get("backupPath"),
        runtime=rt,
        json_output=opts.get("json", False),
    )

    logger["info"](f"Migration context built for provider: {opts.get('provider', 'unknown')}")
    logger["debug"](f"Config: {context.get('config', {})}")

    result: dict[str, Any] = {
        "success": True,
        "provider": opts.get("provider"),
        "configWritten": False,
        "backupCreated": False,
    }

    if not opts.get("yes"):
        logger["info"]("Dry run or confirmation required. Use --yes to apply.")
        return result

    config = context.get("config", {})
    config_path = os.path.expanduser("~/.openclaw/openclaw.json")

    if not opts.get("noBackup"):
        backup_dir = os.path.expanduser("~/.openclaw/backups")
        if opts.get("backupOutput"):
            backup_dir = opts["backupOutput"]
        backup_path = _backup_file(config_path, backup_dir)
        if backup_path:
            result["backupCreated"] = True
            result["backupPath"] = backup_path
            logger["info"](f"Backup created: {backup_path}")

    try:
        _write_config(config_path, config)
        result["configWritten"] = True
        logger["info"](f"Config written to: {config_path}")
    except Exception as e:
        result["success"] = False
        logger["error"](f"Failed to write config: {e}")

    return result
