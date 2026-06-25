"""Parses execution directives for approval, sandbox, and target settings.

Extracts and removes `/exec` options from message text.
"""

from __future__ import annotations

import re
from typing import Any, Literal

ExecTarget = Literal["local", "remote", "sandbox"]
ExecSecurity = Literal["deny", "allowlist", "full"]
ExecAsk = Literal["off", "on-miss", "always"]


def _normalize_optional_lowercase_string(value: str | None) -> str | None:
    if not value or not isinstance(value, str):
        return None
    trimmed = value.strip().lower()
    return trimmed or None


def _normalize_exec_target(value: str | None) -> ExecTarget | None:
    normalized = _normalize_optional_lowercase_string(value)
    if normalized in ("local", "remote", "sandbox"):
        return normalized  # type: ignore[return-value]
    return None


def _normalize_exec_security(value: str | None) -> ExecSecurity | None:
    normalized = _normalize_optional_lowercase_string(value)
    if normalized in ("deny", "allowlist", "full"):
        return normalized  # type: ignore[return-value]
    return None


def _normalize_exec_ask(value: str | None) -> ExecAsk | None:
    normalized = _normalize_optional_lowercase_string(value)
    if normalized in ("off", "on-miss", "always"):
        return normalized  # type: ignore[return-value]
    return None


def _skip_directive_arg_prefix(raw: str) -> int:
    """Skip whitespace and optional colon after /exec."""
    i = 0
    while i < len(raw) and raw[i] in (" ", "\t"):
        i += 1
    if i < len(raw) and raw[i] == ":":
        i += 1
        while i < len(raw) and raw[i] in (" ", "\t"):
            i += 1
    return i


def _take_directive_token(raw: str, start: int) -> tuple[str | None, int]:
    """Take a whitespace-delimited token from raw starting at start."""
    i = start
    while i < len(raw) and raw[i] in (" ", "\t"):
        i += 1
    if i >= len(raw):
        return None, i
    token_start = i
    while i < len(raw) and raw[i] not in (" ", "\t"):
        i += 1
    return raw[token_start:i], i


def _split_token(token: str) -> dict[str, str] | None:
    """Split a token into key=value or key:value."""
    eq = token.find("=")
    colon = token.find(":")
    if eq == -1 and colon == -1:
        return None
    if eq == -1:
        idx = colon
    elif colon == -1:
        idx = eq
    else:
        idx = min(eq, colon)
    key = _normalize_optional_lowercase_string(token[:idx])
    value = token[idx + 1:].strip()
    if not key:
        return None
    return {"key": key, "value": value}


def _parse_exec_directive_args(raw: str) -> dict[str, Any]:
    """Parse exec directive arguments from raw text."""
    length = len(raw)
    i = _skip_directive_arg_prefix(raw)
    consumed = i

    result: dict[str, Any] = {
        "consumed": consumed,
        "execHost": None,
        "execSecurity": None,
        "execAsk": None,
        "execNode": None,
        "rawExecHost": None,
        "rawExecSecurity": None,
        "rawExecAsk": None,
        "rawExecNode": None,
        "hasExecOptions": False,
        "invalidHost": False,
        "invalidSecurity": False,
        "invalidAsk": False,
        "invalidNode": False,
    }

    while i < length:
        token, next_i = _take_directive_token(raw, i)
        if token is None:
            break
        i = next_i
        parsed = _split_token(token)
        if not parsed:
            break
        key = parsed["key"]
        value = parsed["value"]

        if key == "host":
            result["rawExecHost"] = value
            target = _normalize_exec_target(value)
            result["execHost"] = target
            if not target:
                result["invalidHost"] = True
            result["hasExecOptions"] = True
            consumed = i
            continue
        if key == "security":
            result["rawExecSecurity"] = value
            security = _normalize_exec_security(value)
            result["execSecurity"] = security
            if not security:
                result["invalidSecurity"] = True
            result["hasExecOptions"] = True
            consumed = i
            continue
        if key == "ask":
            result["rawExecAsk"] = value
            ask = _normalize_exec_ask(value)
            result["execAsk"] = ask
            if not ask:
                result["invalidAsk"] = True
            result["hasExecOptions"] = True
            consumed = i
            continue
        if key == "node":
            result["rawExecNode"] = value
            trimmed = value.strip()
            if not trimmed:
                result["invalidNode"] = True
            else:
                result["execNode"] = trimmed
            result["hasExecOptions"] = True
            consumed = i
            continue
        break

    result["consumed"] = consumed
    return result


def extract_exec_directive(body: str | None) -> dict[str, Any]:
    """Extract and remove `/exec` options from message text."""
    if not body:
        return {
            "cleaned": "",
            "hasDirective": False,
            "hasExecOptions": False,
            "invalidHost": False,
            "invalidSecurity": False,
            "invalidAsk": False,
            "invalidNode": False,
        }

    match = re.search(r"(?:^|\s)/exec(?=$|\s|:)", body, re.IGNORECASE)
    if not match:
        return {
            "cleaned": body.strip(),
            "hasDirective": False,
            "hasExecOptions": False,
            "invalidHost": False,
            "invalidSecurity": False,
            "invalidAsk": False,
            "invalidNode": False,
        }

    start = match.start() + match.group().index("/exec")
    args_start = start + len("/exec")
    parsed = _parse_exec_directive_args(body[args_start:])

    cleaned_raw = body[:start] + " " + body[args_start + parsed["consumed"]:]
    cleaned = re.sub(r"\s+", " ", cleaned_raw).strip()

    return {
        "cleaned": cleaned,
        "hasDirective": True,
        "execHost": parsed["execHost"],
        "execSecurity": parsed["execSecurity"],
        "execAsk": parsed["execAsk"],
        "execNode": parsed["execNode"],
        "rawExecHost": parsed["rawExecHost"],
        "rawExecSecurity": parsed["rawExecSecurity"],
        "rawExecAsk": parsed["rawExecAsk"],
        "rawExecNode": parsed["rawExecNode"],
        "hasExecOptions": parsed["hasExecOptions"],
        "invalidHost": parsed["invalidHost"],
        "invalidSecurity": parsed["invalidSecurity"],
        "invalidAsk": parsed["invalidAsk"],
        "invalidNode": parsed["invalidNode"],
    }
