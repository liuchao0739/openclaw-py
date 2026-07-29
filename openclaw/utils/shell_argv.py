from __future__ import annotations

import re

DOUBLE_QUOTE_ESCAPES = {"\\", '"', "$", "`", "\n", "\r"}
_WHITESPACE_RE = re.compile(r"\s")


def _is_double_quote_escape(next_ch: str | None) -> bool:
    return bool(next_ch and next_ch in DOUBLE_QUOTE_ESCAPES)


def split_shell_args(raw: str) -> list[str] | None:
    tokens: list[str] = []
    buf = ""
    in_single = False
    in_double = False
    escaped = False

    def push_token() -> None:
        nonlocal buf
        if buf:
            tokens.append(buf)
            buf = ""

    i = 0
    while i < len(raw):
        ch = raw[i]
        if escaped:
            buf += ch
            escaped = False
            i += 1
            continue
        if not in_single and not in_double and ch == "\\":
            escaped = True
            i += 1
            continue
        if in_single:
            if ch == "'":
                in_single = False
            else:
                buf += ch
            i += 1
            continue
        if in_double:
            next_ch = raw[i + 1] if i + 1 < len(raw) else None
            if ch == "\\" and _is_double_quote_escape(next_ch):
                buf += next_ch
                i += 2
                continue
            if ch == '"':
                in_double = False
            else:
                buf += ch
            i += 1
            continue
        if ch == "'":
            in_single = True
            i += 1
            continue
        if ch == '"':
            in_double = True
            i += 1
            continue
        if ch == "#" and not buf:
            break
        if _WHITESPACE_RE.match(ch):
            push_token()
            i += 1
            continue
        buf += ch
        i += 1

    if escaped or in_single or in_double:
        return None
    push_token()
    return tokens
