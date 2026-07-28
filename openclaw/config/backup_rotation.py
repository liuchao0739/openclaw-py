from __future__ import annotations

import os
import shutil
import time
from pathlib import Path
from typing import Any


def maintain_config_backups(
    config_path: str,
    fs_ops: dict[str, Any] | None = None,
    max_backups: int = 5,
) -> None:
    backup_dir = os.path.join(os.path.dirname(config_path), ".backups")
    if fs_ops:
        _maintain_with_fs_ops(config_path, backup_dir, fs_ops, max_backups)
        return

    os.makedirs(backup_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(backup_dir, f"{os.path.basename(config_path)}.{timestamp}.bak")

    try:
        if os.path.exists(config_path):
            shutil.copy2(config_path, backup_path)
    except (OSError, IOError):
        pass

    _cleanup_old_backups(backup_dir, max_backups)


def _maintain_with_fs_ops(
    config_path: str,
    backup_dir: str,
    fs_ops: dict[str, Any],
    max_backups: int,
) -> None:
    os.makedirs(backup_dir, exist_ok=True)
    timestamp = time.strftime("%Y%m%d-%H%M%S")
    backup_path = os.path.join(backup_dir, f"{os.path.basename(config_path)}.{timestamp}.bak")

    try:
        copy_fn = fs_ops.get("copyFile", shutil.copy2)
        if os.path.exists(config_path):
            copy_fn(config_path, backup_path)
    except (OSError, IOError):
        pass

    _cleanup_old_backups(backup_dir, max_backups)


def _cleanup_old_backups(backup_dir: str, max_backups: int) -> None:
    try:
        backups = sorted(
            [
                os.path.join(backup_dir, f)
                for f in os.listdir(backup_dir)
                if f.endswith(".bak")
            ],
            key=os.path.getmtime,
            reverse=True,
        )
        for old_backup in backups[max_backups:]:
            try:
                os.remove(old_backup)
            except (OSError, IOError):
                pass
    except (OSError, IOError):
        pass
