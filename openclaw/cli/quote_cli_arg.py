from __future__ import annotations

import re

_SAFE_ARG_RE = re.compile(r"^[A-Za-z0-9_/:=.,@%+-]+$")


def quote_cli_arg(value: str) -> str:
    if _SAFE_ARG_RE.match(value):
        return value
    return "'" + value.replace("'", "'\\''") + "'"
