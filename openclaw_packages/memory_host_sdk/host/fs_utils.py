from __future__ import annotations

import os
from pathlib import Path
from typing import Optional


class WalkDirectoryEntry:
    def __init__(self, path: str, name: str, kind: str):
        self.path = path
        self.name = name
        self.kind = kind


def walk_directory(
    dir_path: str,
    symlinks: str = "skip",
    descend: Optional[callable] = None,
    include: Optional[callable] = None,
) -> dict:
    entries: list[WalkDirectoryEntry] = []
    root = Path(dir_path)

    def _walk(current: Path) -> None:
        try:
            for item in current.iterdir():
                abs_path = str(item.resolve() if item.is_symlink() else item)
                name = item.name
                if item.is_symlink():
                    if symlinks == "skip":
                        continue
                if item.is_dir():
                    entry = WalkDirectoryEntry(abs_path, name, "directory")
                    if descend is None or descend(entry):
                        entries.append(entry)
                        _walk(item)
                elif item.is_file():
                    entry = WalkDirectoryEntry(abs_path, name, "file")
                    if include is None or include(entry):
                        entries.append(entry)
        except (PermissionError, OSError):
            pass

    _walk(root)
    return {"entries": entries}


class RegularFileStatResult:
    def __init__(self, missing: bool = False, stat: Optional[os.stat_result] = None):
        self.missing = missing
        self.stat = stat


def stat_regular_file(file_path: str) -> RegularFileStatResult:
    try:
        st = os.stat(file_path)
        return RegularFileStatResult(missing=False, stat=st)
    except FileNotFoundError:
        return RegularFileStatResult(missing=True)
    except OSError:
        return RegularFileStatResult(missing=True)


async def read_regular_file(file_path: str, max_bytes: Optional[int] = None) -> dict:
    try:
        with open(file_path, "rb") as f:
            if max_bytes:
                data = f.read(max_bytes)
            else:
                data = f.read()
        return {"buffer": data}
    except FileNotFoundError:
        raise
    except OSError:
        raise


def is_file_missing_error(err: object) -> bool:
    if isinstance(err, FileNotFoundError):
        return True
    if isinstance(err, OSError):
        return err.errno in (2, 20)
    if isinstance(err, dict):
        code = err.get("code")
        return code in ("ENOENT", "ENOTDIR", "not-found")
    return False


def is_path_inside(root_path: str, candidate_path: str) -> bool:
    try:
        root = os.path.realpath(root_path)
        candidate = os.path.realpath(candidate_path)
        return candidate.startswith(root + os.sep) or candidate == root
    except OSError:
        return False


def is_path_inside_with_realpath(root_path: str, candidate_path: str) -> bool:
    return is_path_inside(root_path, candidate_path)


async def assert_no_symlink_parents(root_dir: str, target_path: str) -> None:
    current = os.path.dirname(os.path.abspath(target_path))
    root_real = os.path.realpath(root_dir)
    while True:
        if current == os.path.dirname(current):
            break
        if os.path.realpath(current) != current:
            raise ValueError(f"Symlink detected in path: {current}")
        if not is_path_inside(root_real, current):
            break
        current = os.path.dirname(current)


def walk_files(dir_path: str, extensions: Optional[List[str]] = None) -> List[str]:
    results = []
    root = Path(dir_path)
    if not root.exists():
        return results
    for item in root.rglob("*"):
        if item.is_file():
            if extensions is None:
                results.append(str(item))
            else:
                suffixes = tuple(ext if ext.startswith(".") else f".{ext}" for ext in extensions)
                if item.name.endswith(suffixes):
                    results.append(str(item))
    return results


def stat_file(file_path: str) -> Optional[dict]:
    try:
        st = os.stat(file_path)
        return {
            "path": file_path,
            "size": st.st_size,
            "mtimeMs": int(st.st_mtime * 1000),
            "mode": st.st_mode,
            "isFile": os.path.isfile(file_path),
            "isDirectory": os.path.isdir(file_path),
        }
    except OSError:
        return None


async def root(root_dir: str):
    class Root:
        def __init__(self, base: str):
            self._base = base

        async def resolve(self, rel_path: str) -> str:
            abs_path = os.path.join(self._base, rel_path)
            real = os.path.realpath(abs_path)
            if not real.startswith(self._base):
                raise ValueError(f"Path escapes root: {rel_path}")
            return real

    return Root(root_dir)
