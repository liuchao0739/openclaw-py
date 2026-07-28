from __future__ import annotations

from typing import Any

from .shiki_curated_languages import (
    BASE_LANGUAGE_ALIASES,
    BASE_LANGUAGE_HINTS,
)


def normalize_optional_string(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


async def normalize_supported_language_hint(
    value: str | None,
    options: dict[str, Any] | None = None,
) -> str | None:
    normalized = normalize_optional_string(value)
    if not normalized:
        return None
    base_alias = BASE_LANGUAGE_ALIASES.get(normalized)
    if base_alias:
        return base_alias
    if normalized in BASE_LANGUAGE_HINTS:
        return normalized
    if not options or not options.get("languagePackAvailable"):
        return None
    return normalized


async def normalize_supported_language_hints(
    values: list[str],
    options: dict[str, Any],
) -> list[str]:
    supported: set[str] = set()
    for value in values:
        normalized = await normalize_supported_language_hint(value, options)
        if not normalized:
            continue
        supported.add(normalized)
    if options.get("fallbackToText") and not supported:
        supported.add("text")
    return list(supported)


def collect_diff_payload_language_hints(payload: dict[str, Any]) -> list[str]:
    langs: set[str] = set()
    file_diff = payload.get("fileDiff")
    if file_diff and isinstance(file_diff, dict):
        lang = file_diff.get("lang")
        if lang:
            langs.add(lang)
    old_file = payload.get("oldFile")
    if old_file and isinstance(old_file, dict):
        lang = old_file.get("lang")
        if lang:
            langs.add(lang)
    new_file = payload.get("newFile")
    if new_file and isinstance(new_file, dict):
        lang = new_file.get("lang")
        if lang:
            langs.add(lang)
    return list(langs)


async def normalize_diff_payload_file_language(
    file: dict[str, Any] | None,
    options: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    if not file:
        return None
    lang = file.get("lang")
    if not isinstance(lang, str):
        return file
    normalized = await normalize_supported_language_hint(lang, options)
    if lang == normalized:
        return file
    if not normalized:
        result = dict(file)
        result["lang"] = "text"
        return result
    result = dict(file)
    result["lang"] = normalized
    return result


async def normalize_diff_viewer_payload_languages(
    payload: dict[str, Any],
    options: dict[str, Any] | None = None,
) -> dict[str, Any]:
    file_diff = await normalize_diff_payload_file_language(payload.get("fileDiff"), options)
    old_file = await normalize_diff_payload_file_language(payload.get("oldFile"), options)
    new_file = await normalize_diff_payload_file_language(payload.get("newFile"), options)
    payload_langs = await normalize_supported_language_hints(
        payload.get("langs", []),
        {"fallbackToText": False, **(options or {})},
    )
    langs: set[str] = set(payload_langs)
    for lang in collect_diff_payload_language_hints({
        "fileDiff": file_diff,
        "oldFile": old_file,
        "newFile": new_file,
    }):
        langs.add(lang)
    if not langs:
        langs.add("text")
    result = dict(payload)
    result["fileDiff"] = file_diff
    result["oldFile"] = old_file
    result["newFile"] = new_file
    result["langs"] = list(langs)
    return result


def is_base_diff_viewer_language(lang: str) -> bool:
    return lang in BASE_LANGUAGE_HINTS