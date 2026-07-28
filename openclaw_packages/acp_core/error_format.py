from __future__ import annotations

import json
import re
from typing import Any, Callable

SECRET_PATTERNS: list[re.Pattern[str]] = [
    re.compile(r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CARD[_-]?NUMBER|CARD[_-]?CVC|CARD[_-]?CVV|CVC|CVV|SECURITY[_-]?CODE|PAYMENT[_-]?CREDENTIAL|SHARED[_-]?PAYMENT[_-]?TOKEN)\b\s*[=:]\s*([\"']?)([^\s\"'\\]+)\1", re.IGNORECASE),
    re.compile(r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD|CARD[_-]?NUMBER|CARD[_-]?CVC|CARD[_-]?CVV|CVC|CVV|SECURITY[_-]?CODE|PAYMENT[_-]?CREDENTIAL|SHARED[_-]?PAYMENT[_-]?TOKEN)\b\s*[=:]\s*\+([\"'])([^\s\"'\\]+)\+\1", re.IGNORECASE),
    re.compile(r"[?&](?:access[-_]?token|auth[-_]?token|hook[-_]?token|refresh[-_]?token|api[-_]?key|client[-_]?secret|token|key|secret|password|pass|passwd|auth|signature|card[-_]?number|card[-_]?cvc|card[-_]?cvv|cvc|cvv|security[-_]?code|payment[-_]?credential|shared[-_]?payment[-_]?token)=([^&\s\"'<>]+)", re.IGNORECASE),
    re.compile(r'"(?:apiKey|token|secret|password|passwd|accessToken|refreshToken|cardNumber|card_number|cardCvc|card_cvc|cardCvv|card_cvv|cvc|cvv|securityCode|security_code|paymentCredential|payment_credential|sharedPaymentToken|shared_payment_token)"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r'(^|[\s,{])["\']?(?:api[-_]key|access[-_]token|refresh[-_]token|authToken|auth[-_]token|clientSecret|client[-_]secret|appSecret|app[-_]secret)["\']?\s*[:=]\s*([\"\'])([^\"\'\r\n]+)\2', re.IGNORECASE),
    re.compile(r'(^|[\s,{])["\']?(?:authorization|proxy-authorization|cookie|set-cookie|x-api-key|x-auth-token)["\']?\s*[:=]\s*([\"\'])([^\"\'\r\n]+)\2', re.IGNORECASE),
    re.compile(r"--(?:api[-_]?key|hook[-_]?token|token|secret|password|passwd|card[-_]?number|card[-_]?cvc|card[-_]?cvv|cvc|cvv|security[-_]?code|payment[-_]?credential|shared[-_]?payment[-_]?token)\s+([\"']?)([^\s\"']+)\1", re.IGNORECASE),
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+([A-Za-z0-9._\-+=]+)", re.IGNORECASE),
    re.compile(r"Authorization\s*[:=]\s*Basic\s+([A-Za-z0-9+/=]+)", re.IGNORECASE),
    re.compile(r"(?:X-OpenClaw-Token|x-pomerium-jwt-assertion|X-Api-Key|X-Auth-Token)\s*[:=]\s*([^\s\"',;]+)", re.IGNORECASE),
    re.compile(r"\bBearer\s+([A-Za-z0-9._\-+=]{18,})\b", re.IGNORECASE),
    re.compile(r"(^|[\s,;])(?:access_token|refresh_token|auth[-_]?token|api[-_]?key|client[-_]?secret|app[-_]?secret|token|secret|password|passwd|card[-_]?number|card[-_]?cvc|card[-_]?cvv|cvc|cvv|security[-_]?code|payment[-_]?credential|shared[-_]?payment[-_]?token)=([^\s&#]+)", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----", re.IGNORECASE),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{8,})\b"),
    re.compile(r"(ghp_[A-Za-z0-9]{20,})"),
    re.compile(r"(github_pat_[A-Za-z0-9_]{20,})"),
    re.compile(r"(xox[baprs]-[A-Za-z0-9-]{10,})"),
    re.compile(r"(xapp-[A-Za-z0-9-]{10,})"),
    re.compile(r"(gsk_[A-Za-z0-9_-]{10,})"),
    re.compile(r"(AIza[0-9A-Za-z\-_]{20,})"),
    re.compile(r"(ya29\.[0-9A-Za-z_\-./+=]{10,})"),
    re.compile(r"(1\/\/0[0-9A-Za-z_\-./+=]{10,})"),
    re.compile(r"(eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,})"),
    re.compile(r"(pplx-[A-Za-z0-9_-]{10,})"),
    re.compile(r"(npm_[A-Za-z0-9]{10,})"),
    re.compile(r"(AKID[A-Za-z0-9]{10,})"),
    re.compile(r"(LTAI[A-Za-z0-9]{10,})"),
    re.compile(r"(hf_[A-Za-z0-9]{10,})"),
    re.compile(r"(r8_[A-Za-z0-9]{10,})"),
    re.compile(r"\bbot(\d{6,}:[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(\d{6,}:[A-Za-z0-9_-]{20,})\b"),
]

_configured_redactor: Callable[[str], str] | None = None


def configure_acp_error_redactor(redactor: Callable[[str], str] | None) -> None:
    global _configured_redactor
    _configured_redactor = redactor


def redact_sensitive_text(value: str) -> str:
    if _configured_redactor is not None:
        return _configured_redactor(value)

    def _replace(match: re.Match[str]) -> str:
        if "PRIVATE KEY-----" in match.group(0):
            return "[REDACTED_PRIVATE_KEY]"
        groups = match.groups()
        for group in reversed(groups):
            if isinstance(group, str) and len(group) > 0:
                return match.group(0).replace(group, "[REDACTED]")
        return "[REDACTED]"

    redacted = value
    for pattern in SECRET_PATTERNS:
        redacted = pattern.sub(_replace, redacted)
    return redacted


def stringify_non_error_cause(value: Any) -> str:
    if value is None:
        return "null"
    if isinstance(value, str):
        return value
    if isinstance(value, (int, float, bool)):
        return str(value)
    try:
        return json.dumps(value) if not isinstance(value, (int, float, bool)) else str(value)
    except (TypeError, ValueError):
        return str(value)