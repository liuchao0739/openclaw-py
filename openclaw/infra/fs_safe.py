from __future__ import annotations

import json
import os
import shutil
from pathlib import Path
from typing import Any


class FsSafeRoot:
    def __init__(self, root_path: str, **kwargs):
        self.root_path = os.path.realpath(root_path)
        self.hardlinks = kwargs.get("hardlinks", "reject")
        self.mkdir = kwargs.get("mkdir", True)
        self.mode = kwargs.get("mode", 0o600)
        self.symlinks = kwargs.get("symlinks", "reject")

    @property
    def root_real(self) -> str:
        return self.root_path

    def _resolve_safe_path(self, relative_path: str) -> str:
        full_path = os.path.realpath(os.path.join(self.root_path, relative_path))
        if not full_path.startswith(self.root_path):
            raise ValueError(f"Path escapes root: {relative_path}")
        return full_path

    def exists(self, relative_path: str) -> bool:
        safe_path = self._resolve_safe_path(relative_path)
        return os.path.exists(safe_path)

    def read_text(self, relative_path: str) -> str:
        safe_path = self._resolve_safe_path(relative_path)
        with open(safe_path, "r", encoding="utf-8") as f:
            return f.read()

    def read_bytes(self, relative_path: str) -> bytes:
        safe_path = self._resolve_safe_path(relative_path)
        with open(safe_path, "rb") as f:
            return f.read()

    def write(
        self,
        relative_path: str,
        content: str | bytes,
        *,
        mkdir: bool = True,
        mode: int | None = None,
        overwrite: bool = True,
    ) -> None:
        safe_path = self._resolve_safe_path(relative_path)
        if mkdir:
            os.makedirs(os.path.dirname(safe_path), exist_ok=True)

        if not overwrite and os.path.exists(safe_path):
            raise FileExistsError(f"File already exists: {safe_path}")

        if isinstance(content, str):
            with open(safe_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            with open(safe_path, "wb") as f:
                f.write(content)

        if mode is not None:
            os.chmod(safe_path, mode)

    def remove(self, relative_path: str) -> None:
        safe_path = self._resolve_safe_path(relative_path)
        try:
            os.remove(safe_path)
        except FileNotFoundError:
            pass

    def list(self, relative_path: str = "") -> list[str]:
        safe_path = self._resolve_safe_path(relative_path)
        if not os.path.isdir(safe_path):
            return []
        return os.listdir(safe_path)

    def move(self, src_relative: str, dst_relative: str, *, overwrite: bool = True) -> None:
        src_safe = self._resolve_safe_path(src_relative)
        dst_safe = self._resolve_safe_path(dst_relative)
        if not overwrite and os.path.exists(dst_safe):
            raise FileExistsError(f"Destination already exists: {dst_safe}")
        os.makedirs(os.path.dirname(dst_safe), exist_ok=True)
        shutil.move(src_safe, dst_safe)

    def open(self, relative_path: str, mode: str = "r") -> Any:
        safe_path = self._resolve_safe_path(relative_path)
        return open(safe_path, mode)


def create_fs_root(root_path: str, **kwargs) -> FsSafeRoot:
    return FsSafeRoot(root_path, **kwargs)
