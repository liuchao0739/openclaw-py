from __future__ import annotations

from typing import Any


class FailoverErrorReason:
    AUTH = "auth"
    AUTH_PERMANENT = "auth_permanent"
    BILLING = "billing"
    RATE_LIMIT = "rate_limit"
    OVERLOADED = "overloaded"
    TIMEOUT = "timeout"
    MODEL_NOT_FOUND = "model_not_found"
    SERVER_ERROR = "server_error"
    SESSION_EXPIRED = "session_expired"
    FORMAT = "format"
    EMPTY_RESPONSE = "empty_response"
    NO_ERROR_DETAILS = "no_error_details"
    UNCLASSIFIED = "unclassified"
    UNKNOWN = "unknown"


def classify_failover_error(error: Any) -> str:
    if error is None:
        return FailoverErrorReason.UNKNOWN
    message = str(error).lower()

    keywords: dict[str, list[str]] = {
        FailoverErrorReason.AUTH_PERMANENT: [
            "invalid api key", "unauthorized", "authentication failed",
            "invalid api_key", "401", "bad request.*api key",
        ],
        FailoverErrorReason.BILLING: [
            "billing", "insufficient", "quota exceeded", "payment",
            "out of credits", "402",
        ],
        FailoverErrorReason.RATE_LIMIT: [
            "rate limit", "too many requests", "429", "throttl",
        ],
        FailoverErrorReason.OVERLOADED: [
            "overloaded", "capacity", "503", "service unavailable",
        ],
        FailoverErrorReason.TIMEOUT: [
            "timeout", "timed out", "connection error", "504",
        ],
        FailoverErrorReason.SERVER_ERROR: [
            "500", "internal server error", "server error",
        ],
        FailoverErrorReason.MODEL_NOT_FOUND: [
            "model not found", "no such model", "404.*model",
        ],
        FailoverErrorReason.SESSION_EXPIRED: [
            "session expired", "token expired", "refresh token",
            "oauth.*expired",
        ],
        FailoverErrorReason.FORMAT: [
            "invalid response", "parse error", "malformed",
            "json.*error", "validation error",
        ],
    }

    for reason, patterns in keywords.items():
        for pattern in patterns:
            import re
            if re.search(pattern, message):
                return reason

    return FailoverErrorReason.UNCLASSIFIED
