from __future__ import annotations

import json
import os
import secrets
import shutil
import time
from pathlib import Path
from typing import Any

from openclaw.plugin_sdk.temp_path import resolve_preferred_openclaw_tmp_dir

DEFAULT_TTL_MS = 30 * 60 * 1000
MAX_TTL_MS = 6 * 60 * 60 * 1000
SWEEP_FALLBACK_AGE_MS = 24 * 60 * 60 * 1000
DEFAULT_CLEANUP_INTERVAL_MS = 5 * 60 * 1000
VIEWER_PREFIX = "/plugins/diffs/view"


def _normalize_ttl_ms(value: int | None) -> int:
    if value is None or not isinstance(value, int) or value <= 0:
        return DEFAULT_TTL_MS
    return min(value, MAX_TTL_MS)


def _resolve_expires_at_iso(created_at_ms: int, ttl_ms: int) -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime((created_at_ms + ttl_ms) / 1000))


def _is_expired(meta: dict[str, Any]) -> bool:
    expires_at = meta.get("expiresAt", "")
    try:
        expires_ts = time.mktime(time.strptime(expires_at, "%Y-%m-%dT%H:%M:%S.000Z")) * 1000
    except (ValueError, OverflowError):
        return True
    return time.time() * 1000 >= expires_ts


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _normalize_artifact_context(value: Any) -> dict[str, Any] | None:
    if not isinstance(value, dict):
        return None
    raw = value
    context = {
        "agentId": _normalize_optional_string(raw.get("agentId")),
        "sessionId": _normalize_optional_string(raw.get("sessionId")),
        "messageChannel": _normalize_optional_string(raw.get("messageChannel")),
        "agentAccountId": _normalize_optional_string(raw.get("agentAccountId")),
    }
    if any(v is not None for v in context.values()):
        return context
    return None


class DiffArtifactStore:
    def __init__(self, root_dir: str, logger: Any = None, cleanup_interval_ms: int | None = None):
        self._root_dir = Path(root_dir).resolve()
        self._logger = logger
        self._cleanup_interval_ms = (
            cleanup_interval_ms
            if cleanup_interval_ms is not None
            else DEFAULT_CLEANUP_INTERVAL_MS
        )
        self._cleanup_in_flight: Any = None
        self._next_cleanup_at = 0

    async def create_artifact(self, params: dict[str, Any]) -> dict[str, Any]:
        await self._ensure_root()
        artifact_id = secrets.token_hex(10)
        token = secrets.token_hex(24)
        artifact_dir = self._artifact_dir(artifact_id)
        html_path = artifact_dir / "viewer.html"
        ttl_ms = _normalize_ttl_ms(params.get("ttlMs"))
        created_at = time.time()
        created_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(created_at))
        expires_at = _resolve_expires_at_iso(int(created_at * 1000), ttl_ms)
        meta: dict[str, Any] = {
            "id": artifact_id,
            "token": token,
            "title": params.get("title", ""),
            "inputKind": params.get("inputKind", ""),
            "fileCount": params.get("fileCount", 0),
            "createdAt": created_at_iso,
            "expiresAt": expires_at,
            "viewerPath": f"{VIEWER_PREFIX}/{artifact_id}/{token}",
            "htmlPath": str(html_path),
        }
        context = params.get("context")
        if context:
            meta["context"] = context
        artifact_dir.mkdir(parents=True, exist_ok=True)
        html_path.write_text(params.get("html", ""), encoding="utf-8")
        await self._write_meta(meta)
        self._schedule_cleanup()
        return meta

    async def get_artifact(self, artifact_id: str, token: str) -> dict[str, Any] | None:
        meta = await self._read_meta(artifact_id)
        if not meta:
            return None
        if meta.get("token") != token:
            return None
        if _is_expired(meta):
            await self._delete_artifact(artifact_id)
            return None
        return meta

    async def read_html(self, artifact_id: str) -> str:
        meta = await self._read_meta(artifact_id)
        if not meta:
            raise ValueError(f"Diff artifact not found: {artifact_id}")
        html_path = self._normalize_stored_path(meta.get("htmlPath", ""), "htmlPath")
        return Path(html_path).read_text(encoding="utf-8")

    async def update_file_path(self, artifact_id: str, file_path: str) -> dict[str, Any]:
        meta = await self._read_meta(artifact_id)
        if not meta:
            raise ValueError(f"Diff artifact not found: {artifact_id}")
        normalized = self._normalize_stored_path(file_path, "filePath")
        next_meta = dict(meta)
        next_meta["filePath"] = normalized
        next_meta["imagePath"] = normalized
        await self._write_meta(next_meta)
        return next_meta

    async def update_image_path(self, artifact_id: str, image_path: str) -> dict[str, Any]:
        return await self.update_file_path(artifact_id, image_path)

    def allocate_file_path(self, artifact_id: str, fmt: str = "png") -> str:
        return str(self._artifact_dir(artifact_id) / f"preview.{fmt}")

    async def create_standalone_file_artifact(
        self, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if params is None:
            params = {}
        await self._ensure_root()
        artifact_id = secrets.token_hex(10)
        artifact_dir = self._artifact_dir(artifact_id)
        fmt = params.get("format", "png")
        file_path = str(artifact_dir / f"preview.{fmt}")
        ttl_ms = _normalize_ttl_ms(params.get("ttlMs"))
        created_at = time.time()
        created_at_iso = time.strftime("%Y-%m-%dT%H:%M:%S.000Z", time.gmtime(created_at))
        expires_at = _resolve_expires_at_iso(int(created_at * 1000), ttl_ms)
        meta: dict[str, Any] = {
            "kind": "standalone_file",
            "id": artifact_id,
            "createdAt": created_at_iso,
            "expiresAt": expires_at,
            "filePath": self._normalize_stored_path(file_path, "filePath"),
        }
        context = params.get("context")
        if context:
            meta["context"] = _normalize_artifact_context(context)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        await self._write_standalone_meta(meta)
        self._schedule_cleanup()
        result = {
            "id": artifact_id,
            "filePath": meta["filePath"],
            "expiresAt": meta["expiresAt"],
        }
        if meta.get("context"):
            result["context"] = meta["context"]
        return result

    def allocate_image_path(self, artifact_id: str, fmt: str = "png") -> str:
        return self.allocate_file_path(artifact_id, fmt)

    def _schedule_cleanup(self) -> None:
        self._maybe_cleanup_expired()

    async def cleanup_expired(self) -> None:
        await self._ensure_root()
        entries = list(self._root_dir.iterdir()) if self._root_dir.is_dir() else []
        now = time.time() * 1000
        for entry in entries:
            if not entry.is_dir():
                continue
            artifact_id = entry.name
            meta = await self._read_meta(artifact_id)
            if meta:
                if _is_expired(meta):
                    await self._delete_artifact(artifact_id)
                continue
            standalone_meta = await self._read_standalone_meta(artifact_id)
            if standalone_meta:
                if _is_expired(standalone_meta):
                    await self._delete_artifact(artifact_id)
                continue
            try:
                mtime = entry.stat().st_mtime * 1000
            except OSError:
                continue
            if now - mtime > SWEEP_FALLBACK_AGE_MS:
                await self._delete_artifact(artifact_id)

    async def _ensure_root(self) -> None:
        self._root_dir.mkdir(parents=True, exist_ok=True)

    def _maybe_cleanup_expired(self) -> None:
        now = time.time() * 1000
        if self._cleanup_in_flight is not None or now < self._next_cleanup_at:
            return
        self._next_cleanup_at = now + self._cleanup_interval_ms
        import asyncio

        cleanup_promise = asyncio.ensure_future(self.cleanup_expired())

        def _on_done(fut: asyncio.Future) -> None:
            self._cleanup_in_flight = None

        cleanup_promise.add_done_callback(_on_done)
        self._cleanup_in_flight = cleanup_promise

    def _artifact_dir(self, artifact_id: str) -> Path:
        return self._resolve_within_root(artifact_id)

    async def _write_meta(self, meta: dict[str, Any]) -> None:
        await self._write_json_meta(meta["id"], "meta.json", meta)

    async def _read_meta(self, artifact_id: str) -> dict[str, Any] | None:
        parsed = await self._read_json_meta(artifact_id, "meta.json", "diff artifact")
        if not parsed:
            return None
        return parsed

    async def _write_standalone_meta(self, meta: dict[str, Any]) -> None:
        await self._write_json_meta(meta["id"], "file-meta.json", meta)

    async def _read_standalone_meta(self, artifact_id: str) -> dict[str, Any] | None:
        parsed = await self._read_json_meta(artifact_id, "file-meta.json", "standalone diff")
        if not parsed:
            return None
        try:
            value = parsed
            if (
                value.get("kind") != "standalone_file"
                or not isinstance(value.get("id"), str)
                or not isinstance(value.get("createdAt"), str)
                or not isinstance(value.get("expiresAt"), str)
                or not isinstance(value.get("filePath"), str)
            ):
                return None
            result = {
                "kind": value["kind"],
                "id": value["id"],
                "createdAt": value["createdAt"],
                "expiresAt": value["expiresAt"],
                "filePath": self._normalize_stored_path(value["filePath"], "filePath"),
            }
            if value.get("context"):
                result["context"] = _normalize_artifact_context(value["context"])
            return result
        except Exception:
            if self._logger:
                self._logger.warning(
                    f"Failed to normalize standalone diff metadata for {artifact_id}"
                )
            return None

    async def _write_json_meta(self, artifact_id: str, file_name: str, data: Any) -> None:
        artifact_dir = self._artifact_dir(artifact_id)
        artifact_dir.mkdir(parents=True, exist_ok=True)
        meta_path = artifact_dir / file_name
        meta_path.write_text(json.dumps(data, indent=2), encoding="utf-8")

    async def _read_json_meta(
        self, artifact_id: str, file_name: str, context: str
    ) -> Any:
        meta_path = self._artifact_dir(artifact_id) / file_name
        try:
            raw = meta_path.read_text(encoding="utf-8")
            return json.loads(raw)
        except FileNotFoundError:
            return None
        except Exception as e:
            if self._logger:
                self._logger.warning(f"Failed to read {context} metadata for {artifact_id}: {e}")
            return None

    async def _delete_artifact(self, artifact_id: str) -> None:
        artifact_dir = self._artifact_dir(artifact_id)
        if artifact_dir.exists():
            shutil.rmtree(artifact_dir, ignore_errors=True)

    def _resolve_within_root(self, *parts: str) -> Path:
        candidate = (self._root_dir / Path(*parts)).resolve()
        self._assert_within_root(candidate)
        return candidate

    def _normalize_stored_path(self, raw_path: str, label: str) -> str:
        path_obj = Path(raw_path)
        if path_obj.is_absolute():
            candidate = path_obj.resolve()
        else:
            candidate = (self._root_dir / path_obj).resolve()
        self._assert_within_root(candidate, label)
        return str(candidate)

    def _assert_within_root(self, candidate: Path, label: str = "path") -> None:
        try:
            candidate.relative_to(self._root_dir)
        except ValueError:
            raise ValueError(f"Diff artifact {label} escapes store root: {candidate}")