import os
from pathlib import Path
from urllib.parse import unquote

class FsSafeError(Exception):
    pass


class FsSafeHandle:
    def __init__(self, file_path: str):
        self._file_path = file_path
        self._fd = None

    async def open(self) -> "FsSafeHandle":
        self._fd = open(self._file_path, "rb")
        return self

    async def read_file(self, encoding: str = None):
        if encoding:
            return self._fd.read()
        return self._fd.read()

    async def stat(self) -> dict:
        st = os.stat(self._file_path)
        return {
            "isDirectory": os.path.isdir(self._file_path),
            "isSymbolicLink": os.path.islink(self._file_path),
            "size": st.st_size,
        }

    async def close(self) -> None:
        if self._fd:
            self._fd.close()
            self._fd = None


class FsRoot:
    def __init__(self, root_dir: str):
        self._root_dir = os.path.realpath(root_dir)

    async def open(self, relative: str) -> FsSafeHandle:
        resolved = os.path.realpath(os.path.join(self._root_dir, relative))
        if not (resolved == self._root_dir or resolved.startswith(self._root_dir + os.sep)):
            raise FsSafeError("path escapes root")
        if os.path.islink(resolved):
            raise FsSafeError("symlinks not allowed")
        handle = FsSafeHandle(resolved)
        return await handle.open()

    async def stat(self, relative: str) -> dict:
        resolved = os.path.realpath(os.path.join(self._root_dir, relative))
        if not (resolved == self._root_dir or resolved.startswith(self._root_dir + os.sep)):
            raise FsSafeError("path escapes root")
        if os.path.islink(resolved):
            raise FsSafeError("symlinks not allowed")
        st = os.stat(resolved)
        return {
            "isDirectory": os.path.isdir(resolved),
            "isSymbolicLink": os.path.islink(resolved),
            "size": st.st_size,
        }

    async def write(self, relative: str, data: str) -> None:
        resolved = os.path.realpath(os.path.join(self._root_dir, relative))
        if not (resolved == self._root_dir or resolved.startswith(self._root_dir + os.sep)):
            raise FsSafeError("path escapes root")
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        with open(resolved, "w", encoding="utf-8") as f:
            f.write(data)

    async def write_json(self, relative: str, data, space: int = 2) -> None:
        import json
        text = json.dumps(data, indent=space, ensure_ascii=False)
        await self.write(relative, text)

    async def copy_in(self, relative: str, source_path: str) -> None:
        resolved = os.path.realpath(os.path.join(self._root_dir, relative))
        if not (resolved == self._root_dir or resolved.startswith(self._root_dir + os.sep)):
            raise FsSafeError("path escapes root")
        Path(resolved).parent.mkdir(parents=True, exist_ok=True)
        import shutil
        shutil.copy2(source_path, resolved)


async def fs_root(root_dir: str) -> FsRoot:
    return FsRoot(root_dir)


def normalize_url_path(raw_path: str) -> str:
    decoded = unquote(raw_path or "/")
    normalized = os.path.normpath(decoded)
    normalized = normalized.replace("\\", "/")
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if normalized == "/.":
        return "/"
    return normalized


def _path_escapes_root(decoded_path: str) -> bool:
    depth = 0
    for segment in decoded_path.split("/"):
        if segment == "" or segment == ".":
            continue
        if segment == "..":
            if depth == 0:
                return True
            depth -= 1
            continue
        depth += 1
    return False


def _try_normalize_url_path(raw_path: str) -> str:
    try:
        decoded = unquote(raw_path or "/")
    except Exception:
        return None
    if _path_escapes_root(decoded):
        return None
    normalized = os.path.normpath(decoded).replace("\\", "/")
    if not normalized.startswith("/"):
        normalized = "/" + normalized
    if normalized == "/.":
        return "/"
    return normalized


async def resolve_file_within_root(root_real: str, url_path: str):
    normalized = _try_normalize_url_path(url_path)
    if normalized is None:
        return None
    rel = normalized.lstrip("/")
    if any(p == ".." for p in rel.split("/")):
        return None
    root = await fs_root(root_real)

    async def try_open(relative: str):
        try:
            return await root.open(relative)
        except FsSafeError:
            return None
        except Exception:
            raise

    if normalized.endswith("/"):
        return await try_open(os.path.join(rel, "index.html").replace("\\", "/"))

    try:
        st = await root.stat(rel)
        if st.get("isSymbolicLink"):
            return None
        if st.get("isDirectory"):
            return await try_open(os.path.join(rel, "index.html").replace("\\", "/"))
    except FsSafeError:
        return None
    except Exception:
        raise

    return await try_open(rel)
