import re
from typing import Optional, TypedDict
from urllib.parse import urlparse, urlunparse, parse_qsl, urlencode, unquote


class ConfigUiHintTags(TypedDict, total=False):
    tags: list[str]


SENSITIVE_URL_HINT_TAG = "url-secret"

SENSITIVE_URL_QUERY_PARAM_NAMES = {
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
}

URL_QUERY_NAME_SEPARATOR_RE = re.compile(
    r"[\x00-\x20\x7f-\xa0\u1680\u2000-\u200a\u2028\u2029\u202f\u205f\u3000"
    r"\u115f\u1160\u3164\uffa0\ufeff+]"
)


def _normalize_lowercase_string_or_empty(value):
    return value.strip().lower() if isinstance(value, str) else ""


def _normalize_url_query_param_name(name):
    stripped = URL_QUERY_NAME_SEPARATOR_RE.sub("", name)
    try:
        decoded = unquote(stripped)
        second_stripped = URL_QUERY_NAME_SEPARATOR_RE.sub("", decoded)
        result = _normalize_lowercase_string_or_empty(second_stripped)
    except Exception:
        result = _normalize_lowercase_string_or_empty(stripped)
    return result.replace("-", "_")


def is_sensitive_url_query_param_name(name):
    normalized = _normalize_url_query_param_name(name)
    return normalized in SENSITIVE_URL_QUERY_PARAM_NAMES


def is_sensitive_url_config_path(path):
    if path.endswith(".baseUrl") or path.endswith(".httpUrl"):
        return True
    if path.endswith(".cdpUrl"):
        return True
    if path.endswith(".request.proxy.url"):
        return True
    return bool(re.match(r"^mcp\.servers\.(?:\*|[^.]+)\.url$", path))


def has_sensitive_url_hint_tag(hint):
    if hint is None:
        return False
    tags = hint.get("tags")
    return tags is not None and SENSITIVE_URL_HINT_TAG in tags


def redact_sensitive_url(value):
    try:
        parsed = urlparse(value)
        if not parsed.scheme:
            return value
        mutated = False
        if parsed.username or parsed.password:
            userinfo = ""
            if parsed.username:
                userinfo = "***"
            if parsed.password:
                if userinfo:
                    userinfo += ":***"
                else:
                    userinfo = ":***"
            netloc = parsed.hostname or ""
            if parsed.port is not None:
                netloc = f"{netloc}:{parsed.port}"
            netloc = f"{userinfo}@{netloc}" if userinfo else netloc
            parsed = parsed._replace(netloc=netloc)
            mutated = True
        if parsed.query:
            pairs = parse_qsl(parsed.query, keep_blank_values=True)
            seen_sensitive = set()
            new_pairs = []
            for key, val in pairs:
                if is_sensitive_url_query_param_name(key):
                    if key not in seen_sensitive:
                        new_pairs.append((key, "***"))
                        seen_sensitive.add(key)
                    mutated = True
                else:
                    new_pairs.append((key, val))
            if mutated:
                new_query = urlencode(new_pairs)
                parsed = parsed._replace(query=new_query)
        return urlunparse(parsed) if mutated else value
    except Exception:
        return value


def redact_sensitive_url_like_string(value):
    redacted_url = redact_sensitive_url(value)
    if redacted_url != value:
        return redacted_url
    value = re.sub(r"//([^@/?#\s]+)@", "//***:***@", value)

    def _replace_param(match):
        prefix = match.group(1)
        key = match.group(2)
        if is_sensitive_url_query_param_name(key):
            return f"{prefix}{key}=***"
        return match.group(0)

    return re.sub(r"([?&])([^=&]+)=([^&]*)", _replace_param, value)
