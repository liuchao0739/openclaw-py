from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Any

VIEWER_ASSET_PREFIX = "/plugins/diffs-language-pack/assets/"
VIEWER_LOADER_PATH = f"{VIEWER_ASSET_PREFIX}viewer.js"
VIEWER_RUNTIME_PATH = f"{VIEWER_ASSET_PREFIX}viewer-runtime.js"

VIEWER_RUNTIME_RELATIVE_IMPORT_PATH = "./viewer-runtime.js"
VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS = [
    "./assets/viewer-runtime.js",
    "../assets/viewer-runtime.js",
]

_runtime_asset_cache: dict[str, Any] | None = None


def _is_missing_file_error(error: Exception) -> bool:
    return isinstance(error, FileNotFoundError)


async def resolve_viewer_runtime_file_url() -> str:
    base = str(Path(__file__).resolve())
    for relative_path in VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS:
        candidate = str(Path(base) / relative_path)
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("viewer runtime asset candidates were not found")


async def get_served_viewer_asset(pathname: str) -> dict[str, Any] | None:
    global _runtime_asset_cache
    if pathname != VIEWER_LOADER_PATH and pathname != VIEWER_RUNTIME_PATH:
        return None
    runtime_path = await resolve_viewer_runtime_file_url()
    path_obj = Path(runtime_path)
    stat = path_obj.stat()
    if _runtime_asset_cache and _runtime_asset_cache["mtimeMs"] == stat.st_mtime:
        assets = _runtime_asset_cache
    else:
        runtime_body = path_obj.read_bytes()
        hash_digest = hashlib.sha1(runtime_body).hexdigest()[:12]
        assets = {
            "mtimeMs": stat.st_mtime,
            "runtimeBody": runtime_body,
            "loaderBody": f'import "{VIEWER_RUNTIME_RELATIVE_IMPORT_PATH}?v={hash_digest}";\n',
        }
        _runtime_asset_cache = assets
    if pathname == VIEWER_LOADER_PATH:
        return {
            "body": assets["loaderBody"],
            "contentType": "text/javascript; charset=utf-8",
        }
    return {
        "body": assets["runtimeBody"],
        "contentType": "text/javascript; charset=utf-8",
    }