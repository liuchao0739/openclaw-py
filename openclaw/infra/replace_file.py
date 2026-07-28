from __future__ import annotations

import os
import tempfile
from pathlib import Path
from typing import Any


def replace_file_atomic(
    file_path: str,
    content: str,
    mode: int = 0o600,
    dir_mode: int = 0o700,
    temp_prefix: str = "",
    copy_fallback_on_permission_error: bool = True,
) -> None:
    path_obj = Path(file_path)
    path_obj.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_path = tempfile.mkstemp(
        prefix=temp_prefix or path_obj.name,
        dir=str(path_obj.parent),
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.chmod(tmp_path, mode)
        os.replace(tmp_path, file_path)
    except OSError:
        try:
            os.unlink(tmp_path)
        except OSError:
            pass
        raise


def replace_file_atomic_sync(
    file_path: str,
    content: str,
    mode: int = 0o600,
    dir_mode: int = 0o700,
    temp_prefix: str = "",
    copy_fallback_on_permission_error: bool = True,
) -> None:
    replace_file_atomic(
        file_path=file_path,
        content=content,
        mode=mode,
        dir_mode=dir_mode,
        temp_prefix=temp_prefix,
        copy_fallback_on_permission_error=copy_fallback_on_permission_error,
    )
