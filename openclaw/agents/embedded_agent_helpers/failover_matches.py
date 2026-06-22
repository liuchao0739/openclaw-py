"""Text-pattern matchers for failover and provider errors (subset)."""

from __future__ import annotations

import re
from typing import Pattern

PERIODIC_USAGE_LIMIT_RE = re.compile(
    r"\b(?:daily|weekly|monthly)(?:/(?:daily|weekly|monthly))* (?:usage )?limit(?:s)?(?: (?:exhausted|reached|exceeded))?\b",
    re.I,
)

_RATE_LIMIT = [
    re.compile(r"rate[_ ]limit|too many requests|429", re.I),
    re.compile(r"too many (?:concurrent )?requests", re.I),
    "model_cooldown",
    "quota exceeded",
    "resource_exhausted",
    "throttled",
    "请求过于频繁",
]
_OVERLOADED = [
    re.compile(r"overloaded_error", re.I),
    "overloaded",
    "high demand",
]
_TIMEOUT = [
    "timeout",
    "timed out",
    "deadline exceeded",
    "fetch failed",
    "network error",
    "请求超时",
]
_BILLING = [
    re.compile(r"\b402\b", re.I),
    "payment required",
    "insufficient credits",
    "余额不足",
]
_AUTH = [
    "incorrect api key",
    "invalid token",
    "unauthorized",
    "forbidden",
    re.compile(r"\b401\b"),
    re.compile(r"\b403\b"),
    "认证失败",
]
_FORMAT = [
    "tool_use.id",
    "invalid request format",
    "does not support assistant message prefill",
]


def _norm(raw: str) -> str:
    return (raw or "").strip().lower()


def _matches(raw: str, patterns: list[str | Pattern[str]]) -> bool:
    if not raw:
        return False
    value = _norm(raw)
    for pattern in patterns:
        if isinstance(pattern, re.Pattern):
            if pattern.search(value):
                return True
        elif pattern in value:
            return True
    return False


def is_rate_limit_error_message(raw: str) -> bool:
    return _matches(raw, _RATE_LIMIT)


def is_timeout_error_message(raw: str) -> bool:
    return _matches(raw, _TIMEOUT)


def is_billing_error_message(raw: str) -> bool:
    return _matches(raw, _BILLING)


def is_auth_error_message(raw: str) -> bool:
    return _matches(raw, _AUTH)


def is_overloaded_error_message(raw: str) -> bool:
    return _matches(raw, _OVERLOADED)


def is_server_error_message(raw: str) -> bool:
    value = _norm(raw)
    if not value:
        return False
    return "internal server error" in value or bool(re.search(r"\bhttp\s+5\d\d\b", value, re.I))


def matches_format_error_pattern(raw: str) -> bool:
    return _matches(raw, _FORMAT)


def is_periodic_usage_limit_error_message(raw: str) -> bool:
    return bool(PERIODIC_USAGE_LIMIT_RE.search(raw))


def is_auth_permanent_error_message(raw: str) -> bool:
    return _matches(
        raw,
        [
            "key has been revoked",
            "account has been deactivated",
            re.compile(r"api[_ ]?key[_ ]?(?:revoked|deactivated)", re.I),
        ],
    )