from __future__ import annotations

import os
import re
from typing import Any

from .browser import PlaywrightDiffScreenshotter
from .config import resolve_diff_image_render_options
from .render import render_diff_document
from .types import (
    DIFF_IMAGE_QUALITY_PRESETS,
    DIFF_LAYOUTS,
    DIFF_MODES,
    DIFF_OUTPUT_FORMATS,
    DIFF_THEMES,
    DiffInput,
)
from .url import build_viewer_url, normalize_viewer_base_url

MAX_BEFORE_AFTER_BYTES = 512 * 1024
MAX_PATCH_BYTES = 2 * 1024 * 1024
MAX_TITLE_BYTES = 1024
MAX_PATH_BYTES = 2048
MAX_LANG_BYTES = 128
MAX_DIFF_ARTIFACT_TTL_SECONDS = 21600


def _normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


class _PluginToolInputError(Exception):
    def __init__(self, message: str):
        super().__init__(message)
        self.name = "ToolInputError"


def _normalize_file_quality(file_quality: str | None) -> str | None:
    if file_quality and file_quality in DIFF_IMAGE_QUALITY_PRESETS:
        return file_quality
    return None


def _normalize_output_format(fmt: str | None) -> str | None:
    if fmt and fmt in DIFF_OUTPUT_FORMATS:
        return fmt
    return None


def _is_artifact_only_mode(mode: str) -> bool:
    return mode in ("image", "file")


def _resolve_render_target(mode: str) -> str:
    if mode == "view":
        return "viewer"
    if _is_artifact_only_mode(mode):
        return "image"
    return "both"


def _require_rendered_html(html: str | None, target: str) -> str:
    if html is not None:
        return html
    raise ValueError(f"Missing {target} render output.")


def _build_artifact_details(params: dict[str, Any]) -> dict[str, Any]:
    base_details = params["baseDetails"]
    artifact_file = params["artifactFile"]
    image = params["image"]
    return {
        **base_details,
        "filePath": artifact_file["path"],
        "imagePath": artifact_file["path"],
        "path": artifact_file["path"],
        "fileBytes": artifact_file["bytes"],
        "imageBytes": artifact_file["bytes"],
        "format": image["format"],
        "fileFormat": image["format"],
        "fileQuality": image["qualityPreset"],
        "imageQuality": image["qualityPreset"],
        "fileScale": image["scale"],
        "imageScale": image["scale"],
        "fileMaxWidth": image["maxWidth"],
        "imageMaxWidth": image["maxWidth"],
    }


def _build_file_artifact_message(params: dict[str, Any]) -> str:
    lines: list[str] = []
    viewer_url = params.get("viewerUrl")
    if viewer_url:
        lines.append(f"Diff viewer: {viewer_url}")
    fmt = params.get("format", "png").upper()
    file_path = params.get("filePath", "")
    lines.append(f"Diff {fmt} generated at: {file_path}")
    lines.append("Use the `message` tool with `path` or `filePath` to send this file.")
    return "\n".join(lines)


def _normalize_diff_input(params: dict[str, Any]) -> DiffInput:
    patch = (params.get("patch") or "").strip()
    before = params.get("before")
    after = params.get("after")
    if patch:
        _assert_max_bytes(patch, "patch", MAX_PATCH_BYTES)
        if before is not None or after is not None:
            raise _PluginToolInputError("Provide either patch or before/after input, not both.")
        title = (params.get("title") or "").strip()
        if title:
            _assert_max_bytes(title, "title", MAX_TITLE_BYTES)
        return {
            "kind": "patch",
            "patch": patch,
            "title": title,
        }
    if before is None or after is None:
        raise _PluginToolInputError("Provide patch or both before and after text.")
    _assert_max_bytes(before, "before", MAX_BEFORE_AFTER_BYTES)
    _assert_max_bytes(after, "after", MAX_BEFORE_AFTER_BYTES)
    path_val = _normalize_optional_string(params.get("path"))
    lang = _normalize_optional_string(params.get("lang"))
    title = _normalize_optional_string(params.get("title"))
    if path_val:
        _assert_max_bytes(path_val, "path", MAX_PATH_BYTES)
    if lang:
        _assert_max_bytes(lang, "lang", MAX_LANG_BYTES)
    if title:
        _assert_max_bytes(title, "title", MAX_TITLE_BYTES)
    return {
        "kind": "before_after",
        "before": before,
        "after": after,
        "path": path_val,
        "lang": lang,
        "title": title,
    }


def _assert_max_bytes(value: str, label: str, max_bytes: int) -> None:
    byte_len = len(value.encode("utf-8"))
    if byte_len <= max_bytes:
        return
    raise _PluginToolInputError(f"{label} exceeds maximum size ({max_bytes} bytes).")


def _normalize_base_url(base_url: str | None) -> str | None:
    if not base_url:
        return None
    try:
        return normalize_viewer_base_url(base_url.strip())
    except Exception:
        raise _PluginToolInputError(f"Invalid baseUrl: {base_url}")


def _normalize_mode(mode: str | None, fallback: str) -> str:
    if mode and mode in DIFF_MODES:
        return mode
    return fallback


def _normalize_theme(theme: str | None, fallback: str) -> str:
    if theme and theme in DIFF_THEMES:
        return theme
    return fallback


def _normalize_layout(layout: str | None, fallback: str) -> str:
    if layout and layout in DIFF_LAYOUTS:
        return layout
    return fallback


def _normalize_ttl_ms(ttl_seconds: int | None) -> int | None:
    if ttl_seconds is None or not isinstance(ttl_seconds, (int, float)):
        return None
    ttl_seconds = int(ttl_seconds)
    return int(max(1, min(ttl_seconds, MAX_DIFF_ARTIFACT_TTL_SECONDS)) * 1000)


def _build_artifact_context(context: Any) -> dict[str, Any] | None:
    if not context:
        return None
    artifact_context = {
        "agentId": _normalize_optional_string(getattr(context, "agentId", None)),
        "sessionId": _normalize_optional_string(getattr(context, "sessionId", None)),
        "messageChannel": _normalize_optional_string(getattr(context, "messageChannel", None)),
        "agentAccountId": _normalize_optional_string(getattr(context, "agentAccountId", None)),
    }
    if any(v is not None for v in artifact_context.values()):
        return artifact_context
    return None


async def _render_diff_artifact_file(params: dict[str, Any]) -> dict[str, Any]:
    screenshotter = params.get("screenshotter")
    store = params["store"]
    artifact_id = params.get("artifactId")
    html = params["html"]
    theme = params["theme"]
    image = params["image"]
    ttl_ms = params.get("ttlMs")
    context = params.get("context")
    if artifact_id:
        output_path = store.allocate_file_path(artifact_id, image["format"])
        standalone_artifact = None
    else:
        standalone_artifact = await store.create_standalone_file_artifact({
            "format": image["format"],
            "ttlMs": ttl_ms,
            "context": context,
        })
        output_path = standalone_artifact["filePath"]
    await screenshotter.screenshot_html(
        html=html,
        output_path=output_path,
        theme=theme,
        image=image,
    )
    stat = os.stat(output_path)
    result = {
        "path": output_path,
        "bytes": stat.st_size,
    }
    if standalone_artifact:
        result["artifactId"] = standalone_artifact.get("id")
        result["expiresAt"] = standalone_artifact.get("expiresAt")
    return result


def create_diffs_tool(params: dict[str, Any]) -> dict[str, Any]:
    api = params["api"]
    store = params["store"]
    defaults = params["defaults"]
    viewer_base_url = params.get("viewerBaseUrl")
    language_pack_available = params.get("languagePackAvailable", False)
    screenshotter = params.get("screenshotter")
    context = params.get("context")

    async def _execute(tool_call_id: str, raw_params: dict[str, Any]) -> dict[str, Any]:
        artifact_context = _build_artifact_context(context)
        input_data = _normalize_diff_input(raw_params)
        mode = _normalize_mode(raw_params.get("mode"), defaults.get("mode", "both"))
        theme = _normalize_theme(raw_params.get("theme"), defaults.get("theme", "dark"))
        layout = _normalize_layout(raw_params.get("layout"), defaults.get("layout", "unified"))
        expand_unchanged = raw_params.get("expandUnchanged") is True
        ttl_seconds = raw_params.get("ttlSeconds", defaults.get("ttlSeconds", 1800))
        ttl_ms_val = _normalize_ttl_ms(ttl_seconds)
        file_scale = raw_params.get("fileScale")
        file_max_width = raw_params.get("fileMaxWidth")
        image = resolve_diff_image_render_options({
            "defaults": defaults,
            "fileFormat": _normalize_output_format(
                raw_params.get("fileFormat") or raw_params.get("imageFormat") or raw_params.get("format")
            ),
            "fileQuality": _normalize_file_quality(raw_params.get("fileQuality") or raw_params.get("imageQuality")),
            "fileScale": file_scale,
            "fileMaxWidth": file_max_width,
        })
        render_target = _resolve_render_target(mode)
        rendered = await render_diff_document(
            input_data,
            {
                "presentation": {
                    **defaults,
                    "layout": layout,
                    "theme": theme,
                },
                "image": image,
                "expandUnchanged": expand_unchanged,
                "languagePackAvailable": language_pack_available,
            },
            render_target,
        )
        screenshotter_instance = screenshotter
        if screenshotter_instance is None:
            from .browser import PlaywrightDiffScreenshotter as PW
            screenshotter_instance = PW(config=getattr(api, "config", {}))

        if _is_artifact_only_mode(mode):
            artifact_file = await _render_diff_artifact_file({
                "screenshotter": screenshotter_instance,
                "store": store,
                "html": _require_rendered_html(rendered.get("imageHtml"), "image"),
                "theme": theme,
                "image": image,
                "ttlMs": ttl_ms_val,
                "context": artifact_context,
            })
            content: list[dict[str, Any]] = [{
                "type": "text",
                "text": _build_file_artifact_message({
                    "format": image["format"],
                    "filePath": artifact_file["path"],
                }),
            }]
            details = _build_artifact_details({
                "baseDetails": {
                    **({"artifactId": artifact_file["artifactId"]} if artifact_file.get("artifactId") else {}),
                    **({"expiresAt": artifact_file["expiresAt"]} if artifact_file.get("expiresAt") else {}),
                    "title": rendered["title"],
                    "inputKind": rendered["inputKind"],
                    "fileCount": rendered["fileCount"],
                    "mode": mode,
                    **({"context": artifact_context} if artifact_context else {}),
                },
                "artifactFile": artifact_file,
                "image": image,
            })
            return {"content": content, "details": details}

        artifact = await store.create_artifact({
            "html": _require_rendered_html(rendered.get("html"), "viewer"),
            "title": rendered["title"],
            "inputKind": rendered["inputKind"],
            "fileCount": rendered["fileCount"],
            "ttlMs": ttl_ms_val,
            "context": artifact_context,
        })
        config_obj = getattr(api, "config", {})
        viewer_url = build_viewer_url(
            config=config_obj,
            viewer_path=artifact["viewerPath"],
            base_url=_normalize_base_url(raw_params.get("baseUrl")) or viewer_base_url,
        )
        base_details = {
            "artifactId": artifact["id"],
            "viewerUrl": viewer_url,
            "viewerPath": artifact["viewerPath"],
            "title": artifact["title"],
            "expiresAt": artifact["expiresAt"],
            "inputKind": artifact["inputKind"],
            "fileCount": artifact["fileCount"],
            "mode": mode,
            **({"context": artifact_context} if artifact_context else {}),
        }
        if mode == "view":
            return {
                "content": [{"type": "text", "text": f"Diff viewer ready.\n{viewer_url}"}],
                "details": base_details,
            }
        try:
            artifact_file = await _render_diff_artifact_file({
                "screenshotter": screenshotter_instance,
                "store": store,
                "artifactId": artifact["id"],
                "html": _require_rendered_html(rendered.get("imageHtml"), "image"),
                "theme": theme,
                "image": image,
            })
            await store.update_file_path(artifact["id"], artifact_file["path"])
            return {
                "content": [{
                    "type": "text",
                    "text": _build_file_artifact_message({
                        "format": image["format"],
                        "filePath": artifact_file["path"],
                        "viewerUrl": viewer_url,
                    }),
                }],
                "details": _build_artifact_details({
                    "baseDetails": base_details,
                    "artifactFile": artifact_file,
                    "image": image,
                }),
            }
        except Exception as e:
            if mode == "both":
                return {
                    "content": [{
                        "type": "text",
                        "text": f"Diff viewer ready.\n{viewer_url}\nFile rendering failed: {e}",
                    }],
                    "details": {
                        **base_details,
                        "fileError": str(e),
                        "imageError": str(e),
                    },
                }
            raise

    return {
        "name": "diffs",
        "label": "Diffs",
        "description": "Create a read-only diff viewer from before/after text or a unified patch. Returns a gateway viewer URL for canvas use and can also render the same diff to a PNG or PDF.",
        "parameters": {},
        "execute": _execute,
    }