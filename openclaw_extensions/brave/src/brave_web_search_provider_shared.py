"""Brave Search request normalization and result mapping."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

from openclaw.packages.normalization_core import (
    normalize_lowercase_string_or_empty,
    normalize_optional_string,
)

BRAVE_COUNTRY_CODES = {
    "AR",
    "AU",
    "AT",
    "BE",
    "BR",
    "CA",
    "CL",
    "DK",
    "FI",
    "FR",
    "DE",
    "GR",
    "HK",
    "IN",
    "ID",
    "IT",
    "JP",
    "KR",
    "MY",
    "MX",
    "NL",
    "NZ",
    "NO",
    "CN",
    "PL",
    "PT",
    "PH",
    "RU",
    "SA",
    "ZA",
    "ES",
    "SE",
    "CH",
    "TW",
    "TR",
    "GB",
    "US",
    "ALL",
}

BRAVE_SEARCH_LANG_CODES = {
    "ar",
    "eu",
    "bn",
    "bg",
    "ca",
    "zh-hans",
    "zh-hant",
    "hr",
    "cs",
    "da",
    "nl",
    "en",
    "en-gb",
    "et",
    "fi",
    "fr",
    "gl",
    "de",
    "el",
    "gu",
    "he",
    "hi",
    "hu",
    "is",
    "it",
    "jp",
    "kn",
    "ko",
    "lv",
    "lt",
    "ms",
    "ml",
    "mr",
    "nb",
    "pl",
    "pt-br",
    "pt-pt",
    "pa",
    "ro",
    "ru",
    "sr",
    "sk",
    "sl",
    "es",
    "sv",
    "ta",
    "te",
    "th",
    "tr",
    "uk",
    "vi",
}

BRAVE_SEARCH_LANG_ALIASES = {
    "ja": "jp",
    "zh": "zh-hans",
    "zh-cn": "zh-hans",
    "zh-hk": "zh-hant",
    "zh-sg": "zh-hans",
    "zh-tw": "zh-hant",
}

BRAVE_UI_LANG_LOCALE = re.compile(r"^([a-z]{2})-([a-z]{2})$", re.IGNORECASE)


def _normalize_brave_search_lang(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    lower = normalize_lowercase_string_or_empty(trimmed)
    canonical = BRAVE_SEARCH_LANG_ALIASES.get(lower, lower)
    if canonical not in BRAVE_SEARCH_LANG_CODES:
        return None
    return canonical


def normalize_brave_country(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    canonical = trimmed.upper()
    return canonical if canonical in BRAVE_COUNTRY_CODES else "ALL"


def _normalize_brave_ui_lang(value: str | None) -> str | None:
    if not value:
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    match = BRAVE_UI_LANG_LOCALE.match(trimmed)
    if not match:
        return None
    language, region = match.groups()
    return f"{normalize_lowercase_string_or_empty(language)}-{region.upper()}"


def resolve_brave_config(search_config: dict[str, Any] | None = None) -> dict[str, Any]:
    if not search_config:
        return {}
    brave = search_config.get("brave")
    if isinstance(brave, dict) and not isinstance(brave, list):
        return dict(brave)
    return {}


def resolve_brave_mode(brave: dict[str, Any] | None = None) -> str:
    if brave and brave.get("mode") == "llm-context":
        return "llm-context"
    return "web"


def normalize_brave_language_params(
    params: dict[str, str | None],
) -> dict[str, Any]:
    raw_search_lang = normalize_optional_string(params.get("search_lang"))
    raw_ui_lang = normalize_optional_string(params.get("ui_lang"))
    search_lang_candidate = raw_search_lang
    ui_lang_candidate = raw_ui_lang

    if _normalize_brave_ui_lang(raw_search_lang) and _normalize_brave_search_lang(raw_ui_lang):
        search_lang_candidate = raw_ui_lang
        ui_lang_candidate = raw_search_lang

    search_lang = _normalize_brave_search_lang(search_lang_candidate)
    if search_lang_candidate and not search_lang:
        return {"invalidField": "search_lang"}

    ui_lang = _normalize_brave_ui_lang(ui_lang_candidate)
    if ui_lang_candidate and not ui_lang:
        return {"invalidField": "ui_lang"}

    result: dict[str, Any] = {}
    if search_lang:
        result["search_lang"] = search_lang
    if ui_lang:
        result["ui_lang"] = ui_lang
    return result


def _resolve_site_name(url: str | None) -> str | None:
    if not url:
        return None
    try:
        return urlparse(url).hostname
    except ValueError:
        return None


def map_brave_llm_context_results(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    grounding = data.get("grounding")
    generic = grounding.get("generic") if isinstance(grounding, dict) else None
    generic_results = generic if isinstance(generic, list) else []
    results: list[dict[str, Any]] = []
    for entry in generic_results:
        if not isinstance(entry, dict):
            continue
        url = entry.get("url") or ""
        title = entry.get("title") or ""
        raw_snippets = entry.get("snippets")
        snippets = (
            [snippet for snippet in raw_snippets if isinstance(snippet, str) and snippet]
            if isinstance(raw_snippets, list)
            else []
        )
        site_name = _resolve_site_name(url if isinstance(url, str) else None)
        results.append(
            {
                "url": url,
                "title": title,
                "snippets": snippets,
                **({"siteName": site_name} if site_name else {}),
            }
        )
    return results
