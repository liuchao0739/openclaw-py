import re
import os
import uuid
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, List, Optional, TypedDict, Union

from .host.a2ui_shared import CANVAS_HOST_PATH
from .host.file_resolver import fs_root

CANVAS_DOCUMENTS_DIR_NAME = "documents"


class CanvasDocumentAsset(TypedDict, total=False):
    logicalPath: str
    sourcePath: str
    contentType: Optional[str]


class CanvasDocumentManifest(TypedDict, total=False):
    id: str
    kind: str
    title: Optional[str]
    preferredHeight: Optional[int]
    createdAt: str
    entryUrl: str
    localEntrypoint: Optional[str]
    externalUrl: Optional[str]
    surface: Optional[str]
    assets: List[dict]


class CanvasDocumentResolvedAsset(TypedDict, total=False):
    logicalPath: str
    contentType: Optional[str]
    url: str
    localPath: str


def _is_pdf_path_like(value: str) -> bool:
    return bool(re.search(r"\.pdf(?:[?#].*)?$", value.strip(), re.IGNORECASE))


def _escape_html(value: str) -> str:
    return (
        value.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
        .replace("'", "&#39;")
    )


def _build_pdf_wrapper(url: str) -> str:
    escaped = _escape_html(url)
    return f'<!doctype html><html><body style="margin:0;background:#e5e7eb;"><object data="{escaped}" type="application/pdf" style="width:100%;height:100vh;border:0;"><iframe src="{escaped}" style="width:100%;height:100vh;border:0;"></iframe><p style="padding:16px;font:14px system-ui,sans-serif;">Unable to render PDF preview. <a href="{escaped}" target="_blank" rel="noopener noreferrer">Open PDF</a>.</p></object></body></html>'


def _has_control_character(value: str) -> bool:
    for char in value:
        code = ord(char)
        if code < 0x20 or code == 0x7F:
            return True
    return False


def _normalize_logical_path(value: str) -> str:
    normalized = value.replace("\\", "/").lstrip("/")
    parts = [p for p in normalized.split("/") if p]
    if (
        len(parts) == 0
        or any(p in (".", "..") or ":" in p or _has_control_character(p) for p in parts)
    ):
        raise ValueError("canvas document logicalPath invalid")
    return "/".join(parts)


def _canvas_document_id() -> str:
    return f"cv_{uuid.uuid4().hex}"


def _normalize_canvas_document_id(value: str) -> str:
    normalized = value.strip()
    if (
        not normalized
        or normalized in (".", "..")
        or not re.match(r"^[A-Za-z0-9._-]+$", normalized)
    ):
        raise ValueError("canvas document id invalid")
    return normalized


def _resolve_state_dir() -> str:
    return os.environ.get("OPENCLAW_STATE_DIR") or os.path.expanduser("~/.openclaw")


def _resolve_user_path(path: str) -> str:
    return os.path.expanduser(path)


def _resolve_canvas_root_dir(root_dir: Optional[str] = None, state_dir: str = None) -> str:
    if state_dir is None:
        state_dir = _resolve_state_dir()
    if root_dir and root_dir.strip():
        resolved = _resolve_user_path(root_dir)
    else:
        resolved = os.path.join(state_dir, "canvas")
    return str(Path(resolved).resolve())


def _resolve_canvas_documents_dir(root_dir: Optional[str] = None, state_dir: str = None) -> str:
    return os.path.join(_resolve_canvas_root_dir(root_dir, state_dir), CANVAS_DOCUMENTS_DIR_NAME)


def resolve_canvas_document_dir(
    document_id: str,
    root_dir: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> str:
    return os.path.join(
        _resolve_canvas_documents_dir(root_dir, state_dir), document_id
    )


def build_canvas_document_entry_url(document_id: str, entrypoint: str) -> str:
    normalized_entrypoint = _normalize_logical_path(entrypoint)
    from urllib.parse import quote
    encoded_entrypoint = "/".join(quote(seg, safe="") for seg in normalized_entrypoint.split("/"))
    return f"{CANVAS_HOST_PATH}/{CANVAS_DOCUMENTS_DIR_NAME}/{quote(document_id, safe='')}/{encoded_entrypoint}"


def _build_canvas_document_asset_url(document_id: str, logical_path: str) -> str:
    return build_canvas_document_entry_url(document_id, logical_path)


def resolve_canvas_http_path_to_local_path(
    request_path: str,
    root_dir: Optional[str] = None,
    state_dir: Optional[str] = None,
) -> Optional[str]:
    from urllib.parse import unquote
    trimmed = request_path.strip()
    prefix = f"{CANVAS_HOST_PATH}/{CANVAS_DOCUMENTS_DIR_NAME}/"
    if not trimmed.startswith(prefix):
        return None

    path_without_query = re.sub(r"[?#].*$", "", trimmed)
    relative = path_without_query[len(prefix):]
    segments: List[str] = []
    for segment in relative.split("/"):
        if not segment:
            continue
        try:
            segments.append(unquote(segment))
        except Exception:
            return None

    if len(segments) < 2:
        return None

    raw_document_id = segments[0]
    entry_segments = segments[1:]
    try:
        document_id = _normalize_canvas_document_id(raw_document_id)
        normalized_entrypoint = _normalize_logical_path("/".join(entry_segments))
        documents_dir = str(Path(_resolve_canvas_documents_dir(root_dir, state_dir)).resolve())
        candidate_path = str(
            Path(resolve_canvas_document_dir(document_id, root_dir, state_dir)).resolve()
            / normalized_entrypoint
        )
        if not (candidate_path == documents_dir or candidate_path.startswith(documents_dir + os.sep)):
            return None
        return candidate_path
    except Exception:
        return None


def _sanitize_untrusted_file_name(name: str, fallback: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", name) or fallback
    return sanitized


async def _write_manifest(root, manifest: CanvasDocumentManifest) -> None:
    import json
    await root.write_json("manifest.json", manifest, space=2)


async def _copy_assets(
    root, assets: Optional[List[CanvasDocumentAsset]], workspace_dir: str
) -> List[dict]:
    copied: List[dict] = []
    for asset in assets or []:
        logical_path = _normalize_logical_path(asset["logicalPath"])
        source_path = asset["sourcePath"]
        if source_path.startswith("~"):
            resolved_source = _resolve_user_path(source_path)
        elif os.path.isabs(source_path):
            resolved_source = str(Path(source_path).resolve())
        else:
            resolved_source = str(Path(workspace_dir).resolve() / source_path)
        await root.copy_in(logical_path, resolved_source)
        entry = {"logicalPath": logical_path}
        if asset.get("contentType"):
            entry["contentType"] = asset["contentType"]
        copied.append(entry)
    return copied


async def _materialize_entrypoint(
    root_dir: str,
    root,
    input: dict,
    workspace_dir: str,
) -> dict:
    entrypoint = input.get("entrypoint")
    if not entrypoint:
        raise ValueError("canvas document entrypoint required")

    if entrypoint["type"] == "html":
        file_name = "index.html"
        await root.write(file_name, entrypoint["value"])
        return {
            "localEntrypoint": file_name,
            "entryUrl": build_canvas_document_entry_url(os.path.basename(root_dir), file_name),
        }

    if entrypoint["type"] == "url":
        if input["kind"] == "document" and _is_pdf_path_like(entrypoint["value"]):
            file_name = "index.html"
            await root.write(file_name, _build_pdf_wrapper(entrypoint["value"]))
            return {
                "localEntrypoint": file_name,
                "externalUrl": entrypoint["value"],
                "entryUrl": build_canvas_document_entry_url(os.path.basename(root_dir), file_name),
            }
        return {
            "externalUrl": entrypoint["value"],
            "entryUrl": entrypoint["value"],
        }

    entrypoint_value = entrypoint["value"]
    if entrypoint_value.startswith("~"):
        resolved_path = _resolve_user_path(entrypoint_value)
    elif os.path.isabs(entrypoint_value):
        resolved_path = str(Path(entrypoint_value).resolve())
    else:
        resolved_path = str(Path(workspace_dir).resolve() / entrypoint_value)

    if input["kind"] in ("image", "video_asset"):
        copied_name = _sanitize_untrusted_file_name(os.path.basename(resolved_path), "asset")
        await root.copy_in(copied_name, resolved_path)
        if input["kind"] == "image":
            wrapper = f'<!doctype html><html><body style="margin:0;background:#0f172a;display:flex;align-items:center;justify-content:center;"><img src="{_escape_html(copied_name)}" style="max-width:100%;max-height:100vh;object-fit:contain;" /></body></html>'
        else:
            wrapper = f'<!doctype html><html><body style="margin:0;background:#0f172a;"><video src="{_escape_html(copied_name)}" controls autoplay style="width:100%;height:100vh;object-fit:contain;background:#000;"></video></body></html>'
        await root.write("index.html", wrapper)
        return {
            "localEntrypoint": "index.html",
            "entryUrl": build_canvas_document_entry_url(os.path.basename(root_dir), "index.html"),
        }

    file_name = _sanitize_untrusted_file_name(os.path.basename(resolved_path), "document")
    await root.copy_in(file_name, resolved_path)
    if input["kind"] == "document" and _is_pdf_path_like(file_name):
        await root.write("index.html", _build_pdf_wrapper(file_name))
        return {
            "localEntrypoint": "index.html",
            "entryUrl": build_canvas_document_entry_url(os.path.basename(root_dir), "index.html"),
        }
    return {
        "localEntrypoint": file_name,
        "entryUrl": build_canvas_document_entry_url(os.path.basename(root_dir), file_name),
    }


async def create_canvas_document(
    input: dict,
    state_dir: Optional[str] = None,
    workspace_dir: Optional[str] = None,
    canvas_root_dir: Optional[str] = None,
) -> CanvasDocumentManifest:
    ws_dir = workspace_dir or os.getcwd()
    input_id = input.get("id", "")
    doc_id = _normalize_canvas_document_id(input_id) if input_id and input_id.strip() else _canvas_document_id()
    root_dir = resolve_canvas_document_dir(doc_id, root_dir=canvas_root_dir, state_dir=state_dir)

    try:
        shutil.rmtree(root_dir)
    except Exception:
        pass
    Path(root_dir).mkdir(parents=True, exist_ok=True)

    root = await fs_root(root_dir)
    assets = await _copy_assets(root, input.get("assets"), ws_dir)
    entry = await _materialize_entrypoint(root_dir, root, input, ws_dir)

    manifest: CanvasDocumentManifest = {
        "id": doc_id,
        "kind": input["kind"],
        "createdAt": datetime.now(timezone.utc).isoformat(),
        "entryUrl": entry["entryUrl"],
        "assets": assets,
    }

    title = input.get("title", "")
    if title and title.strip():
        manifest["title"] = title.strip()
    if isinstance(input.get("preferredHeight"), (int, float)):
        manifest["preferredHeight"] = input["preferredHeight"]
    if input.get("surface"):
        manifest["surface"] = input["surface"]
    if entry.get("localEntrypoint"):
        manifest["localEntrypoint"] = entry["localEntrypoint"]
    if entry.get("externalUrl"):
        manifest["externalUrl"] = entry["externalUrl"]

    await _write_manifest(root, manifest)
    return manifest


def resolve_canvas_document_assets(
    manifest: CanvasDocumentManifest,
    base_url: Optional[str] = None,
    state_dir: Optional[str] = None,
    canvas_root_dir: Optional[str] = None,
) -> List[CanvasDocumentResolvedAsset]:
    resolved_base_url = None
    if base_url and base_url.strip():
        resolved_base_url = base_url.strip().rstrip("/")
    document_dir = resolve_canvas_document_dir(
        manifest["id"], root_dir=canvas_root_dir, state_dir=state_dir
    )
    result: List[CanvasDocumentResolvedAsset] = []
    for asset in manifest.get("assets", []):
        entry: CanvasDocumentResolvedAsset = {
            "logicalPath": asset["logicalPath"],
            "localPath": os.path.join(document_dir, asset["logicalPath"]),
            "url": (
                f"{resolved_base_url}{_build_canvas_document_asset_url(manifest['id'], asset['logicalPath'])}"
                if resolved_base_url
                else _build_canvas_document_asset_url(manifest["id"], asset["logicalPath"])
            ),
        }
        if asset.get("contentType"):
            entry["contentType"] = asset["contentType"]
        result.append(entry)
    return result
