from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Any


VIEWER_ASSET_PREFIX = "/plugins/diffs/assets/"
VIEWER_LOADER_PATH = f"{VIEWER_ASSET_PREFIX}viewer.js"
VIEWER_RUNTIME_PATH = f"{VIEWER_ASSET_PREFIX}viewer-runtime.js"
LANGUAGE_PACK_VIEWER_ASSET_PREFIX = "/plugins/diffs-language-pack/assets/"
LANGUAGE_PACK_VIEWER_LOADER_PATH = f"{LANGUAGE_PACK_VIEWER_ASSET_PREFIX}viewer.js"
LANGUAGE_PACK_VIEWER_RUNTIME_PATH = f"{LANGUAGE_PACK_VIEWER_ASSET_PREFIX}viewer-runtime.js"

VIEWER_RUNTIME_RELATIVE_IMPORT_PATH = "./viewer-runtime.js"
VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS = [
    "./assets/viewer-runtime.js",
    "../assets/viewer-runtime.js",
]
LANGUAGE_PACK_RUNTIME_CANDIDATE_RELATIVE_PATHS = [
    "../../diffs-language-pack/assets/viewer-runtime.js",
    "../diffs-language-pack/assets/viewer-runtime.js",
]

_runtime_asset_cache: dict[str, Any] | None = None
_language_pack_runtime_asset_cache: dict[str, Any] | None = None


def _is_missing_file_error(error: Exception) -> bool:
    return isinstance(error, FileNotFoundError) or (
        hasattr(error, "errno") and error.errno == 2
    )


async def resolve_viewer_runtime_file_url(base_url: str | None = None) -> str:
    if base_url is None:
        base_url = str(Path(__file__).resolve())
    for relative_path in VIEWER_RUNTIME_CANDIDATE_RELATIVE_PATHS:
        candidate = str(Path(base_url) / relative_path)
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("viewer runtime asset candidates were not found")


async def get_served_viewer_asset(pathname: str) -> dict[str, Any] | None:
    if pathname != VIEWER_LOADER_PATH and pathname != VIEWER_RUNTIME_PATH:
        return None
    assets = await _load_viewer_assets()
    if pathname == VIEWER_LOADER_PATH:
        return {
            "body": assets["loaderBody"],
            "contentType": "text/javascript; charset=utf-8",
        }
    if pathname == VIEWER_RUNTIME_PATH:
        return {
            "body": assets["runtimeBody"],
            "contentType": "text/javascript; charset=utf-8",
        }
    return None


async def get_served_language_pack_viewer_asset(pathname: str) -> dict[str, Any] | None:
    if (
        pathname != LANGUAGE_PACK_VIEWER_LOADER_PATH
        and pathname != LANGUAGE_PACK_VIEWER_RUNTIME_PATH
    ):
        return None
    global _language_pack_runtime_asset_cache
    try:
        runtime_path = await _resolve_runtime_file_url(LANGUAGE_PACK_RUNTIME_CANDIDATE_RELATIVE_PATHS)
        assets = await _load_runtime_assets(
            runtime_path,
            _language_pack_runtime_asset_cache,
            lambda cache: setattr(
                _language_pack_runtime_asset_cache,
                "__setitem__",
                lambda k, v: None,
            ),
        )
        if pathname == LANGUAGE_PACK_VIEWER_LOADER_PATH:
            return {
                "body": assets["loaderBody"],
                "contentType": "text/javascript; charset=utf-8",
            }
        return {
            "body": assets["runtimeBody"],
            "contentType": "text/javascript; charset=utf-8",
        }
    except FileNotFoundError:
        return None


async def _load_viewer_assets() -> dict[str, Any]:
    runtime_path = await resolve_viewer_runtime_file_url()
    return await _load_runtime_assets(runtime_path, _runtime_asset_cache, _update_runtime_cache)


def _update_runtime_cache(cache: dict[str, Any]) -> None:
    global _runtime_asset_cache
    _runtime_asset_cache = cache


async def _load_runtime_assets(
    runtime_path: str,
    cache: dict[str, Any] | None,
    update_cache: Any,
) -> dict[str, Any]:
    path_obj = Path(runtime_path)
    stat = path_obj.stat()
    if cache and cache["mtimeMs"] == stat.st_mtime:
        return cache
    runtime_body = path_obj.read_bytes()
    hash_digest = hashlib.sha1(runtime_body).hexdigest()[:12]
    result = {
        "mtimeMs": stat.st_mtime,
        "runtimeBody": runtime_body,
        "loaderBody": f'import "{VIEWER_RUNTIME_RELATIVE_IMPORT_PATH}?v={hash_digest}";\n',
    }
    update_cache(result)
    return result


async def _resolve_runtime_file_url(relative_paths: list[str]) -> str:
    base = str(Path(__file__).resolve())
    for relative_path in relative_paths:
        candidate = str(Path(base) / relative_path)
        if Path(candidate).is_file():
            return candidate
    raise FileNotFoundError("viewer runtime asset candidates were not found")