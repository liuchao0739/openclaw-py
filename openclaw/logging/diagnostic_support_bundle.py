"""Diagnostic support bundle helpers collect logs and metadata for support exports.

Mirrors src/logging/diagnostic-support-bundle.ts.
"""

from __future__ import annotations

import json
import os
from typing import Any


def _support_bundle_byte_length(content: str) -> int:
    return len(content.encode("utf-8"))


def _assert_safe_bundle_relative_path(path_name: str) -> str:
    normalized = path_name.replace("\\", "/")
    if (
        not normalized
        or normalized.startswith("/")
        or any(part in ("", ".", "..") for part in normalized.split("/"))
    ):
        raise ValueError(f"Invalid bundle file path: {path_name}")
    return normalized


def json_support_bundle_file(path_name: str, value: Any) -> dict[str, Any]:
    return {
        "path": _assert_safe_bundle_relative_path(path_name),
        "mediaType": "application/json",
        "content": json.dumps(value, indent=2) + "\n",
    }


def jsonl_support_bundle_file(path_name: str, lines: list[str]) -> dict[str, Any]:
    return {
        "path": _assert_safe_bundle_relative_path(path_name),
        "mediaType": "application/x-ndjson",
        "content": "\n".join(lines) + "\n",
    }


def text_support_bundle_file(path_name: str, content: str) -> dict[str, Any]:
    return {
        "path": _assert_safe_bundle_relative_path(path_name),
        "mediaType": "text/plain; charset=utf-8",
        "content": content if content.endswith("\n") else content + "\n",
    }


def support_bundle_contents(files: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [
        {"path": f["path"], "mediaType": f["mediaType"], "bytes": _support_bundle_byte_length(f["content"])}
        for f in files
    ]


def _resolve_support_bundle_file_path(output_dir: str, path_name: str) -> str:
    safe_path = _assert_safe_bundle_relative_path(path_name)
    resolved_base = os.path.abspath(output_dir)
    resolved_file = os.path.abspath(os.path.join(resolved_base, safe_path))
    if resolved_file == resolved_base or not resolved_file.startswith(resolved_base + os.sep):
        raise ValueError(f"Bundle file path escaped output directory: {path_name}")
    return resolved_file


def _prepare_support_bundle_directory(output_dir: str) -> None:
    os.makedirs(os.path.dirname(output_dir), exist_ok=True)
    os.makedirs(output_dir, exist_ok=True)


def _write_support_bundle_file(output_dir: str, file: dict[str, Any]) -> None:
    file_path = _resolve_support_bundle_file_path(output_dir, file["path"])
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "x", encoding="utf-8") as f:
        f.write(file["content"])


def write_support_bundle_directory(params: dict[str, Any]) -> list[dict[str, Any]]:
    _prepare_support_bundle_directory(params["outputDir"])
    for file in params["files"]:
        _write_support_bundle_file(params["outputDir"], file)
    return support_bundle_contents(params["files"])


def write_support_bundle_zip(params: dict[str, Any]) -> int:
    import zipfile
    zip_path = params["outputPath"]
    os.makedirs(os.path.dirname(zip_path), exist_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file in params["files"]:
            zf.writestr(_assert_safe_bundle_relative_path(file["path"]), file["content"])
    return os.path.getsize(zip_path)


__all__ = [
    "json_support_bundle_file",
    "jsonl_support_bundle_file",
    "text_support_bundle_file",
    "support_bundle_contents",
    "write_support_bundle_directory",
    "write_support_bundle_zip",
]
