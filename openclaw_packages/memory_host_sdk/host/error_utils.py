from __future__ import annotations

import json
import re
from typing import Any, Optional


SECRET_PATTERNS = [
    re.compile(r"\b[A-Z0-9_]*(?:KEY|TOKEN|SECRET|PASSWORD|PASSWD)\b\s*[=:]\s*([\"']?)([^\s\"'\\]+)\1", re.IGNORECASE),
    re.compile(r"[?&](?:access[-_]?token|auth[-_]?token|hook[-_]?token|refresh[-_]?token|api[-_]?key|client[-_]?secret|token|key|secret|password|pass|passwd|auth|signature)=([^&\s\"'<>]+)", re.IGNORECASE),
    re.compile(r'"(?:apiKey|token|secret|password|passwd|accessToken|refreshToken)"\s*:\s*"([^"]+)"', re.IGNORECASE),
    re.compile(r"--(?:api[-_]?key|hook[-_]?token|token|secret|password|passwd)\s+([\"']?)([^\s\"']+)\1", re.IGNORECASE),
    re.compile(r"Authorization\s*[:=]\s*Bearer\s+([A-Za-z0-9._\-+=]+)", re.IGNORECASE),
    re.compile(r"\bBearer\s+([A-Za-z0-9._\-+=]{18,})\b"),
    re.compile(r"(^|[\s,;])(?:access_token|refresh_token|api[-_]?key|token|secret|password|passwd)=([^\s&#]+)", re.IGNORECASE),
    re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]+?-----END [A-Z ]*PRIVATE KEY-----"),
    re.compile(r"\b(sk-[A-Za-z0-9_-]{8,})\b"),
    re.compile(r"\b(ghp_[A-Za-z0-9]{20,})\b"),
    re.compile(r"\b(github_pat_[A-Za-z0-9_]{20,})\b"),
    re.compile(r"\b(xox[baprs]-[A-Za-z0-9-]{10,})\b"),
    re.compile(r"\b(xapp-[A-Za-z0-9-]{10,})\b"),
    re.compile(r"\b(gsk_[A-Za-z0-9_-]{10,})\b"),
    re.compile(r"\b(AIza[0-9A-Za-z\-_]{20,})\b"),
    re.compile(r"\b(pplx-[A-Za-z0-9_-]{10,})\b"),
    re.compile(r"\b(npm_[A-Za-z0-9]{10,})\b"),
    re.compile(r"\bbot(\d{6,}:[A-Za-z0-9_-]{20,})\b"),
    re.compile(r"\b(\d{6,}:[A-Za-z0-9_-]{20,})\b"),
]


def mask_token(token: str) -> str:
    if len(token) < 18:
        return "***"
    return f"{token[:6]}...{token[-4:]}"


def redact_pem_block(block: str) -> str:
    lines = [l for l in block.splitlines() if l.strip()]
    if len(lines) < 2:
        return "***"
    return f"{lines[0]}\n...redacted...\n{lines[-1]}"


def redact_match(match: re.Match) -> str:
    groups = match.groups()
    full_match = match.group(0)
    if "PRIVATE KEY-----" in full_match:
        return redact_pem_block(full_match)
    token = next((g for g in groups if g and isinstance(g, str) and len(g) > 0), full_match)
    masked = mask_token(token)
    return masked if token == full_match else full_match.replace(token, masked)


def redact_sensitive_text(text: str) -> str:
    result = text
    for pattern in SECRET_PATTERNS:
        result = pattern.sub(lambda m: redact_match(m), result)
    return result


def format_error_message(err: object) -> str:
    formatted: str
    if isinstance(err, Exception):
        formatted = err.message or err.__class__.__name__ or "Error"
        cause = err.__cause__
        seen = {id(err)}
        while cause and id(cause) not in seen:
            seen.add(id(cause))
            if isinstance(cause, Exception):
                if cause.args:
                    formatted += f" | {cause}"
                cause = cause.__cause__
            elif isinstance(cause, str):
                formatted += f" | {cause}"
                break
            else:
                break
    elif isinstance(err, str):
        formatted = err
    elif isinstance(err, (int, float, bool)):
        formatted = str(err)
    else:
        try:
            formatted = json.dumps(err)
        except Exception:
            formatted = str(err)
    return redact_sensitive_text(formatted)
