"""Diffs Language Pack plugin module implements viewer assets behavior."""

from __future__ import annotations

import hashlib
from dataclasses import dataclass
from pathlib import Path

VIEWER_ASSET_PREFIX = "/plugins/diffs-language-pack/assets/"
VIEWER_LOADER_PATH = f"{VIEWER_ASSET_PREFIX}viewer.js"
VIEWER_RUNTIME_PATH = f"{VIEWER_ASSET_PREFIX}viewer-runtime.js"
VIEWER_RUNTIME_RELATIVE_IMPORT_PATH = "./viewer-runtime.js"
VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS = (
    "./assets/viewer-runtime.js",
    "../assets/viewer-runtime.js",
)


@dataclass(frozen=True)
class ServedViewerAsset:
    body: str | bytes
    content_type: str


@dataclass
class RuntimeAssetCache:
    mtime_ns: int
    runtime_body: bytes
    loader_body: str


_runtime_asset_cache: RuntimeAssetCache | None = None
_MODULE_DIR = Path(__file__).resolve().parent


def resolve_viewer_runtime_file_path() -> Path:
    missing_file_error: FileNotFoundError | None = None

    for relative_path in VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS:
        candidate_path = (_MODULE_DIR / relative_path).resolve()
        if candidate_path.is_file():
            return candidate_path
        if missing_file_error is None:
            missing_file_error = FileNotFoundError(relative_path)

    if missing_file_error is not None:
        raise missing_file_error

    raise RuntimeError("viewer runtime asset candidates were not checked")


async def get_served_viewer_asset(pathname: str) -> ServedViewerAsset | None:
    if pathname not in (VIEWER_LOADER_PATH, VIEWER_RUNTIME_PATH):
        return None

    assets = await load_viewer_assets()
    if pathname == VIEWER_LOADER_PATH:
        return ServedViewerAsset(
            body=assets.loader_body,
            content_type="text/javascript; charset=utf-8",
        )

    return ServedViewerAsset(
        body=assets.runtime_body,
        content_type="text/javascript; charset=utf-8",
    )


async def load_viewer_assets() -> RuntimeAssetCache:
    global _runtime_asset_cache

    runtime_path = resolve_viewer_runtime_file_path()
    runtime_stat = runtime_path.stat()
    if _runtime_asset_cache is not None and _runtime_asset_cache.mtime_ns == runtime_stat.st_mtime_ns:
        return _runtime_asset_cache

    runtime_body = runtime_path.read_bytes()
    digest = hashlib.sha1(runtime_body, usedforsecurity=False).hexdigest()[:12]
    _runtime_asset_cache = RuntimeAssetCache(
        mtime_ns=runtime_stat.st_mtime_ns,
        runtime_body=runtime_body,
        loader_body=f'import "{VIEWER_RUNTIME_RELATIVE_IMPORT_PATH}?v={digest}";\n',
    )
    return _runtime_asset_cache
