from __future__ import annotations

import html as html_module
import json
from typing import Any

from .config import normalize_diff_font_size, normalize_diff_line_spacing
from .language_hints import (
    collect_diff_payload_language_hints,
    is_base_diff_viewer_language,
    normalize_diff_viewer_payload_languages,
)
from .pierre_themes import ensure_pierre_themes_registered
from .types import (
    DIFF_LAYOUTS,
    DIFF_MODES,
    DIFF_THEMES,
    DiffInput,
    DiffRenderOptions,
    DiffRenderTarget,
)

DEFAULT_FILE_NAME = "diff.txt"
MAX_PATCH_FILE_COUNT = 128
MAX_PATCH_TOTAL_LINES = 120_000
VIEWER_LOADER_DOCUMENT_PATH = "../../assets/viewer.js"
LANGUAGE_PACK_VIEWER_LOADER_DOCUMENT_PATH = "../../../diffs-language-pack/assets/viewer.js"


def _escape_css_string(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _escape_html(value: str) -> str:
    return html_module.escape(value)


def _escape_json_script(value: Any) -> str:
    return json.dumps(value).replace("<", "\\u003c")


def _build_diff_title(input_data: DiffInput) -> str:
    title = input_data.get("title", "").strip()
    if title:
        return title
    if input_data.get("kind") == "before_after":
        return input_data.get("path", "").strip() or "Text diff"
    return "Patch diff"


def _resolve_before_after_file_name(input_data: DiffInput, lang: str | None = None) -> str:
    path_val = input_data.get("path", "").strip()
    if path_val:
        return path_val
    if lang and lang != "text":
        return f"diff.{lang.lstrip('.')}"
    return DEFAULT_FILE_NAME


def _build_diff_options(options: DiffRenderOptions) -> dict[str, Any]:
    presentation = options.get("presentation", {})
    font_family = _escape_css_string(presentation.get("fontFamily", "Fira Code"))
    font_size = normalize_diff_font_size(presentation.get("fontSize", 15))
    line_spacing = normalize_diff_line_spacing(presentation.get("lineSpacing", 1.6))
    line_height = max(20, round(font_size * line_spacing))
    return {
        "theme": {
            "light": "pierre-light",
            "dark": "pierre-dark",
        },
        "diffStyle": presentation.get("layout", "unified"),
        "diffIndicators": presentation.get("diffIndicators", "bars"),
        "disableLineNumbers": not presentation.get("showLineNumbers", True),
        "expandUnchanged": options.get("expandUnchanged", False),
        "themeType": presentation.get("theme", "dark"),
        "backgroundEnabled": presentation.get("background", True),
        "overflow": "wrap" if presentation.get("wordWrap", True) else "scroll",
        "unsafeCSS": f"""
:host {{
  --diffs-font-family: "{font_family}", "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --diffs-header-font-family: "{font_family}", "SF Mono", Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
  --diffs-font-size: {font_size}px;
  --diffs-line-height: {line_height}px;
}}

[data-diffs-header] {{
  min-height: 64px;
  padding-inline: 18px 14px;
}}

[data-header-content] {{
  gap: 10px;
}}

[data-metadata] {{
  gap: 10px;
}}

.oc-diff-toolbar {{
  display: inline-flex;
  align-items: center;
  gap: 6px;
  margin-inline-start: 6px;
  flex: 0 0 auto;
}}

.oc-diff-toolbar-button {{
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 24px;
  height: 24px;
  padding: 0;
  margin: 0;
  border: 0;
  border-radius: 0;
  background: transparent;
  color: inherit;
  cursor: pointer;
  opacity: 0.6;
  line-height: 0;
  overflow: visible;
  transition: opacity 120ms ease;
  flex: 0 0 auto;
}}

.oc-diff-toolbar-button:hover {{
  opacity: 1;
}}

.oc-diff-toolbar-button[data-active="true"] {{
  opacity: 0.92;
}}

.oc-diff-toolbar-button svg {{
  display: block;
  width: 16px;
  height: 16px;
  min-width: 16px;
  min-height: 16px;
  overflow: visible;
  flex: 0 0 auto;
  color: inherit;
  fill: currentColor;
  pointer-events: none;
}}
""",
    }


def _build_image_render_options(options: DiffRenderOptions) -> DiffRenderOptions:
    result = dict(options)
    presentation = dict(options.get("presentation", {}))
    presentation["fontSize"] = max(16, normalize_diff_font_size(presentation.get("fontSize", 15)))
    result["presentation"] = presentation
    return result


def _should_render_viewer(target: DiffRenderTarget) -> bool:
    return target in ("viewer", "both")


def _should_render_image(target: DiffRenderTarget) -> bool:
    return target in ("image", "both")


def _build_render_variants(
    options: DiffRenderOptions, target: DiffRenderTarget
) -> dict[str, Any]:
    result: dict[str, Any] = {}
    if _should_render_viewer(target):
        result["viewerOptions"] = _build_diff_options(options)
    if _should_render_image(target):
        result["imageOptions"] = _build_diff_options(_build_image_render_options(options))
    return result


def _render_diff_card(payload: dict[str, Any]) -> str:
    return f"""<section class="oc-diff-card">
    <diffs-container class="oc-diff-host" data-openclaw-diff-host>
      <template shadowrootmode="open">{payload.get('prerenderedHTML', '')}</template>
    </diffs-container>
    <script type="application/json" data-openclaw-diff-payload>{_escape_json_script(payload)}</script>
  </section>"""


def _build_html_document(params: dict[str, Any]) -> str:
    viewer_loader_path = (
        LANGUAGE_PACK_VIEWER_LOADER_DOCUMENT_PATH
        if params.get("viewerRuntime") == "language-pack"
        else VIEWER_LOADER_DOCUMENT_PATH
    )
    return f"""<!doctype html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <meta name="color-scheme" content="dark light" />
    <title>{_escape_html(params.get('title', ''))}</title>
    <style>
      * {{
        box-sizing: border-box;
      }}

      html,
      body {{
        min-height: 100%;
      }}

      html {{
        background: #05070b;
      }}

      body {{
        margin: 0;
        min-height: 100vh;
        padding: 22px;
        font-family:
          "Fira Code",
          "SF Mono",
          Monaco,
          Consolas,
          monospace;
        background: #05070b;
        color: #f8fafc;
      }}

      body[data-theme="light"] {{
        background: #f3f5f8;
        color: #0f172a;
      }}

      .oc-frame {{
        max-width: 1560px;
        margin: 0 auto;
      }}

      .oc-frame[data-render-mode="image"] {{
        max-width: {max(640, round(params.get('imageMaxWidth', 960)))}px;
      }}

      [data-openclaw-diff-root] {{
        display: grid;
        gap: 18px;
      }}

      .oc-diff-card {{
        overflow: hidden;
        border-radius: 18px;
        border: 1px solid rgba(148, 163, 184, 0.16);
        background: rgba(15, 23, 42, 0.14);
        box-shadow: 0 18px 48px rgba(2, 6, 23, 0.22);
      }}

      body[data-theme="light"] .oc-diff-card {{
        border-color: rgba(148, 163, 184, 0.22);
        background: rgba(255, 255, 255, 0.92);
        box-shadow: 0 14px 32px rgba(15, 23, 42, 0.08);
      }}

      .oc-diff-host {{
        display: block;
      }}

      .oc-frame[data-render-mode="image"] .oc-diff-card {{
        min-height: 240px;
      }}

      @media (max-width: 720px) {{
        body {{
          padding: 12px;
        }}

        [data-openclaw-diff-root] {{
          gap: 12px;
        }}
      }}
    </style>
  </head>
  <body data-theme="{params.get('theme', 'dark')}">
    <main class="oc-frame" data-render-mode="{params.get('runtimeMode', 'viewer')}">
      <div data-openclaw-diff-root>
        {params.get('bodyHtml', '')}
      </div>
    </main>
    <script type="module" src="{viewer_loader_path}"></script>
  </body>
</html>"""


def _payload_uses_language_pack(payload: dict[str, Any] | None) -> bool:
    if not payload:
        return False
    langs = payload.get("langs", [])
    return any(not is_base_diff_viewer_language(lang) for lang in langs)


def _build_rendered_section(params: dict[str, Any]) -> dict[str, Any]:
    result: dict[str, Any] = {}
    viewer_payload = params.get("viewerPayload")
    if viewer_payload:
        result["viewer"] = _render_diff_card(viewer_payload)
    image_payload = params.get("imagePayload")
    if image_payload:
        result["image"] = _render_diff_card(image_payload)
    result["usesLanguagePack"] = (
        _payload_uses_language_pack(viewer_payload) or _payload_uses_language_pack(image_payload)
    )
    return result


def _build_rendered_bodies(sections: list[dict[str, Any]]) -> dict[str, Any]:
    viewer_sections = [s["viewer"] for s in sections if "viewer" in s]
    image_sections = [s["image"] for s in sections if "image" in s]
    result: dict[str, Any] = {}
    if viewer_sections:
        result["viewerBodyHtml"] = "\n".join(viewer_sections)
    if image_sections:
        result["imageBodyHtml"] = "\n".join(image_sections)
    return result


async def render_before_after_diff(
    input_data: DiffInput,
    options: DiffRenderOptions,
    target: DiffRenderTarget,
) -> dict[str, Any]:
    ensure_pierre_themes_registered()
    language_pack_available = options.get("languagePackAvailable", False)
    lang = await _normalize_supported_language_hint(
        input_data.get("lang"), language_pack_available
    )
    file_name = _resolve_before_after_file_name(input_data, lang)
    old_file = {
        "name": file_name,
        "contents": input_data.get("before", ""),
    }
    new_file = {
        "name": file_name,
        "contents": input_data.get("after", ""),
    }
    if lang:
        old_file["lang"] = lang
        new_file["lang"] = lang
    variants = _build_render_variants(options, target)
    viewer_options = variants.get("viewerOptions")
    image_options = variants.get("imageOptions")
    viewer_result = None
    image_result = None
    if viewer_options:
        viewer_result = await _preload_multi_file_diff_with_fallback(
            old_file, new_file, viewer_options
        )
    if image_options:
        image_result = await _preload_multi_file_diff_with_fallback(
            old_file, new_file, image_options
        )
    viewer_payload = None
    image_payload = None
    if viewer_result and viewer_options:
        viewer_payload = await _normalize_diff_viewer_payload(
            viewer_result, viewer_options, language_pack_available
        )
    if image_result and image_options:
        image_payload = await _normalize_diff_viewer_payload(
            image_result, image_options, language_pack_available
        )
    section = _build_rendered_section({
        "viewerPayload": viewer_payload,
        "imagePayload": image_payload,
    })
    result = _build_rendered_bodies([section])
    result["fileCount"] = 1
    result["usesLanguagePack"] = section.get("usesLanguagePack", False)
    return result


async def render_patch_diff(
    input_data: DiffInput,
    options: DiffRenderOptions,
    target: DiffRenderTarget,
) -> dict[str, Any]:
    ensure_pierre_themes_registered()
    language_pack_available = options.get("languagePackAvailable", False)
    patch = input_data.get("patch", "")
    files = await _parse_patch_files(patch, language_pack_available)
    if not files:
        raise ValueError("Patch input did not contain any file diffs.")
    if len(files) > MAX_PATCH_FILE_COUNT:
        raise ValueError(f"Patch input contains too many files (max {MAX_PATCH_FILE_COUNT}).")
    total_lines = 0
    for file_diff in files:
        split = file_diff.get("splitLineCount", 0)
        unified = file_diff.get("unifiedLineCount", 0)
        try:
            split_val = int(split)
        except (TypeError, ValueError):
            split_val = 0
        try:
            unified_val = int(unified)
        except (TypeError, ValueError):
            unified_val = 0
        total_lines += max(split_val, unified_val, 0)
    if total_lines > MAX_PATCH_TOTAL_LINES:
        raise ValueError(f"Patch input is too large to render (max {MAX_PATCH_TOTAL_LINES} lines).")
    variants = _build_render_variants(options, target)
    viewer_options = variants.get("viewerOptions")
    image_options = variants.get("imageOptions")
    sections: list[dict[str, Any]] = []
    for file_diff in files:
        viewer_result = None
        image_result = None
        if viewer_options:
            viewer_result = await _preload_file_diff_with_fallback(file_diff, viewer_options)
        if image_options:
            image_result = await _preload_file_diff_with_fallback(file_diff, image_options)
        viewer_payload = None
        image_payload = None
        if viewer_result and viewer_options:
            viewer_payload = await _normalize_diff_viewer_payload_file_diff(
                viewer_result, viewer_options, language_pack_available
            )
        if image_result and image_options:
            image_payload = await _normalize_diff_viewer_payload_file_diff(
                image_result, image_options, language_pack_available
            )
        sections.append(_build_rendered_section({
            "viewerPayload": viewer_payload,
            "imagePayload": image_payload,
        }))
    result = _build_rendered_bodies(sections)
    result["fileCount"] = len(files)
    result["usesLanguagePack"] = any(s.get("usesLanguagePack", False) for s in sections)
    return result


async def _normalize_supported_language_hint(
    value: str | None, language_pack_available: bool
) -> str | None:
    if not value:
        return None
    from .language_hints import normalize_supported_language_hint
    return await normalize_supported_language_hint(
        value, {"languagePackAvailable": language_pack_available}
    )


async def _parse_patch_files(patch: str, language_pack_available: bool) -> list[dict[str, Any]]:
    lines = patch.split("\n")
    files: list[dict[str, Any]] = []
    current_file: dict[str, Any] | None = None
    for line in lines:
        if line.startswith("diff --git"):
            if current_file is not None:
                files.append(current_file)
            current_file = {
                "lang": "text",
                "splitLineCount": 0,
                "unifiedLineCount": 0,
            }
        elif current_file is not None:
            if line.startswith("@@"):
                current_file["unifiedLineCount"] = current_file.get("unifiedLineCount", 0) + 1
            elif line.startswith("+") or line.startswith("-"):
                current_file["splitLineCount"] = current_file.get("splitLineCount", 0) + 1
    if current_file is not None:
        files.append(current_file)
    normalized_files: list[dict[str, Any]] = []
    for file_diff in files:
        lang = file_diff.get("lang", "text")
        normalized_lang = await _normalize_supported_language_hint(lang, language_pack_available)
        if normalized_lang and normalized_lang != lang:
            file_diff = dict(file_diff)
            file_diff["lang"] = normalized_lang
        normalized_files.append(file_diff)
    return normalized_files


async def _preload_file_diff_with_fallback(
    file_diff: dict[str, Any], options: dict[str, Any]
) -> dict[str, Any]:
    try:
        return await _do_preload_file_diff(file_diff, options)
    except TypeError as e:
        if 'needs an import attribute of "type: json"' not in str(e):
            raise
        return {
            "fileDiff": file_diff,
            "prerenderedHTML": "",
        }


async def _preload_multi_file_diff_with_fallback(
    old_file: dict[str, Any], new_file: dict[str, Any], options: dict[str, Any]
) -> dict[str, Any]:
    try:
        return await _do_preload_multi_file_diff(old_file, new_file, options)
    except TypeError as e:
        if 'needs an import attribute of "type: json"' not in str(e):
            raise
        return {
            "oldFile": old_file,
            "newFile": new_file,
            "prerenderedHTML": "",
        }


async def _do_preload_file_diff(file_diff: dict[str, Any], options: dict[str, Any]) -> dict[str, Any]:
    return {
        "fileDiff": file_diff,
        "prerenderedHTML": "",
    }


async def _do_preload_multi_file_diff(
    old_file: dict[str, Any], new_file: dict[str, Any], options: dict[str, Any]
) -> dict[str, Any]:
    return {
        "oldFile": old_file,
        "newFile": new_file,
        "prerenderedHTML": "",
    }


async def _normalize_diff_viewer_payload(
    result: dict[str, Any], options: dict[str, Any], language_pack_available: bool
) -> dict[str, Any]:
    payload = {
        "prerenderedHTML": result.get("prerenderedHTML", ""),
        "options": options,
        "langs": [],
        "oldFile": result.get("oldFile"),
        "newFile": result.get("newFile"),
    }
    langs = collect_diff_payload_language_hints({
        "oldFile": result.get("oldFile"),
        "newFile": result.get("newFile"),
    })
    payload["langs"] = langs
    normalized = await normalize_diff_viewer_payload_languages(
        payload, {"languagePackAvailable": language_pack_available}
    )
    return normalized


async def _normalize_diff_viewer_payload_file_diff(
    result: dict[str, Any], options: dict[str, Any], language_pack_available: bool
) -> dict[str, Any]:
    payload = {
        "prerenderedHTML": result.get("prerenderedHTML", ""),
        "options": options,
        "langs": [],
        "fileDiff": result.get("fileDiff"),
    }
    langs = collect_diff_payload_language_hints({
        "fileDiff": result.get("fileDiff"),
    })
    payload["langs"] = langs
    normalized = await normalize_diff_viewer_payload_languages(
        payload, {"languagePackAvailable": language_pack_available}
    )
    return normalized


async def render_diff_document(
    input_data: DiffInput,
    options: DiffRenderOptions,
    target: DiffRenderTarget = "both",
) -> dict[str, Any]:
    title = _build_diff_title(input_data)
    if input_data.get("kind") == "before_after":
        rendered = await render_before_after_diff(input_data, options, target)
    else:
        rendered = await render_patch_diff(input_data, options, target)
    viewer_runtime = "language-pack" if rendered.get("usesLanguagePack") else "base"
    result: dict[str, Any] = {
        "title": title,
        "fileCount": rendered.get("fileCount", 0),
        "inputKind": input_data.get("kind", ""),
        "viewerRuntime": viewer_runtime,
    }
    if rendered.get("viewerBodyHtml"):
        result["html"] = _build_html_document({
            "title": title,
            "bodyHtml": rendered["viewerBodyHtml"],
            "theme": options.get("presentation", {}).get("theme", "dark"),
            "imageMaxWidth": options.get("image", {}).get("maxWidth", 960),
            "runtimeMode": "viewer",
            "viewerRuntime": viewer_runtime,
        })
    if rendered.get("imageBodyHtml"):
        result["imageHtml"] = _build_html_document({
            "title": title,
            "bodyHtml": rendered["imageBodyHtml"],
            "theme": options.get("presentation", {}).get("theme", "dark"),
            "imageMaxWidth": options.get("image", {}).get("maxWidth", 960),
            "runtimeMode": "image",
            "viewerRuntime": viewer_runtime,
        })
    return result