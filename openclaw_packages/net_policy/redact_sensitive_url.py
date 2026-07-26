"""Sensitive URL redaction helpers.

Mirrors packages/net-policy/src/redact-sensitive-url.ts.
"""

from __future__ import annotations

import re
import unicodedata
from typing import TypedDict
from urllib.parse import unquote, urlsplit, urlunsplit

from openclaw.packages.normalization_core import normalize_lowercase_string_or_empty

__all__ = [
    "SENSITIVE_URL_HINT_TAG",
    "has_sensitive_url_hint_tag",
    "is_sensitive_url_config_path",
    "is_sensitive_url_query_param_name",
    "redact_sensitive_url",
    "redact_sensitive_url_like_string",
]

SENSITIVE_URL_HINT_TAG = "url-secret"

_SENSITIVE_URL_QUERY_PARAM_NAMES = frozenset({
    "token",
    "key",
    "api_key",
    "apikey",
    "secret",
    "access_token",
    "auth_token",
    "password",
    "pass",
    "passwd",
    "auth",
    "jwt",
    "session",
    "id_token",
    "code",
    "client_secret",
    "app_secret",
    "hook_token",
    "refresh_token",
    "signature",
    "x_amz_signature",
    "x_amz_security_token",
    "private_key",
    "credential",
    "authorization",
})

_HANGUL_FILLER_CHARS = "\u115f\u1160\u3164\uffa0"


class ConfigUiHintTags(TypedDict, total=False):
    tags: list[str]


def _is_url_query_name_separator(char: str) -> bool:
    if char == "+":
        return True
    if char in _HANGUL_FILLER_CHARS:
        return True
    category = unicodedata.category(char)
    return category.startswith(("C", "Z"))


def _strip_url_query_name_separators(value: str) -> str:
    return "".join(char for char in value if not _is_url_query_name_separator(char))


def _normalize_url_query_param_name(name: str) -> str:
    stripped = _strip_url_query_name_separators(name)
    try:
        from urllib.parse import unquote

        decoded = unquote(stripped)
        normalized = normalize_lowercase_string_or_empty(
            _strip_url_query_name_separators(decoded)
        )
    except ValueError:
        normalized = normalize_lowercase_string_or_empty(stripped)
    return normalized.replace("-", "_")


def is_sensitive_url_query_param_name(name: str) -> bool:
    return _normalize_url_query_param_name(name) in _SENSITIVE_URL_QUERY_PARAM_NAMES


def is_sensitive_url_config_path(path: str) -> bool:
    if path.endswith((".baseUrl", ".httpUrl")):
        return True
    if path.endswith(".cdpUrl"):
        return True
    if path.endswith(".request.proxy.url"):
        return True
    return re.fullmatch(r"mcp\.servers\.(?:\*|[^.]+)\.url", path) is not None


def has_sensitive_url_hint_tag(hint: ConfigUiHintTags | None) -> bool:
    tags = hint.get("tags") if hint else None
    return tags is not None and SENSITIVE_URL_HINT_TAG in tags


def _format_userinfo(username: str | None, password: str | None) -> str:
    if not username and not password:
        return ""
    user = "***" if username else ""
    if password:
        if username:
            return f"{user}:***"
        return ":***"
    return user


def _serialize_query_key_like_url_api(key: str) -> str:
    decoded = unquote(key)
    parts: list[str] = []
    for char in decoded:
        if char == " ":
            parts.append("+")
        elif char.isalnum() or char in "-_.!~*'()+":
            parts.append(char)
        else:
            parts.extend(f"%{byte:02X}" for byte in char.encode("utf-8"))
    return "".join(parts)


def _redact_query_string(query: str) -> tuple[str, bool]:
    if not query:
        return query, False
    mutated = False
    parts: list[str] = []
    for segment in query.split("&"):
        if not segment:
            parts.append(segment)
            continue
        key, separator, _value = segment.partition("=")
        if separator and is_sensitive_url_query_param_name(key):
            parts.append(f"{_serialize_query_key_like_url_api(key)}=***")
            mutated = True
        else:
            parts.append(segment)
    return "&".join(parts), mutated


def redact_sensitive_url(value: str) -> str:
    try:
        split = urlsplit(value)
        if not split.scheme or not split.netloc:
            return value
        mutated = False
        username = split.username
        password = split.password
        netloc = split.netloc
        if username or password:
            host = split.hostname or ""
            if split.port is not None:
                host = f"{host}:{split.port}"
            netloc = f"{_format_userinfo(username, password)}@{host}"
            mutated = True
        query, query_mutated = _redact_query_string(split.query)
        mutated = mutated or query_mutated
        if not mutated:
            return value
        return urlunsplit((split.scheme, netloc, split.path, query, split.fragment))
    except ValueError:
        return value


def redact_sensitive_url_like_string(value: str) -> str:
    redacted_url = redact_sensitive_url(value)
    if redacted_url != value:
        return redacted_url
    redacted = re.sub(r"//([^@/?#\s]+)@", "//***:***@", value)
    return re.sub(
        r"([?&])([^=&]+)=([^&]*)",
        lambda match: (
            f"{match.group(1)}{match.group(2)}=***"
            if is_sensitive_url_query_param_name(match.group(2))
            else match.group(0)
        ),
        redacted,
    )
