"""Plugin HTTP path context canonicalizes request paths for route matching and
protected-route auth checks.

Mirrors src/gateway/server/plugins-http/path-context.ts.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import unquote

# Protected prefixes that always require gateway auth.
PROTECTED_PLUGIN_ROUTE_PREFIXES = ["/admin", "/internal"]

_MAX_DECODE_PASSES = 5


def _normalize_lowercase_string_or_empty(value: str) -> str:
    if isinstance(value, str):
        return value.strip().lower()
    return ""


def _normalize_protected_prefix(prefix: str) -> str:
    collapsed = re.sub(r"/{2,}", "/", _normalize_lowercase_string_or_empty(prefix))
    if len(collapsed) <= 1:
        return collapsed or "/"
    return re.sub(r"/+$", "", collapsed)


_NORMALIZED_PROTECTED_PREFIXES = [
    _normalize_protected_prefix(p) for p in PROTECTED_PLUGIN_ROUTE_PREFIXES
]


@dataclass
class PluginRoutePathContext:
    pathname: str
    canonical_path: str
    candidates: list[str] = field(default_factory=list)
    malformed_encoding: bool = False
    decode_pass_limit_reached: bool = False
    raw_normalized_path: str = ""


def prefix_match_path(pathname: str, prefix: str) -> bool:
    """Match a normalized path against an exact protected prefix boundary."""
    return (
        pathname == prefix
        or pathname.startswith(f"{prefix}/")
        or pathname.startswith(f"{prefix}%")
    )


def is_protected_plugin_route_path_from_context(context: PluginRoutePathContext) -> bool:
    """Return True when any decoded path candidate targets a protected route."""
    if any(
        prefix_match_path(candidate, prefix)
        for candidate in context.candidates
        for prefix in _NORMALIZED_PROTECTED_PREFIXES
    ):
        return True
    if not context.malformed_encoding:
        return False
    return any(
        prefix_match_path(context.raw_normalized_path, prefix)
        for prefix in _NORMALIZED_PROTECTED_PREFIXES
    )


def _canonicalize_path_for_security(pathname: str) -> dict:
    """Build security-relevant decoded path candidates for a request path."""
    raw_normalized = _normalize_lowercase_string_or_empty(pathname)
    candidates: list[str] = []
    malformed = False
    decode_pass_limit_reached = False

    current = pathname
    for _ in range(_MAX_DECODE_PASSES + 1):
        if current not in candidates:
            candidates.append(current)
        try:
            decoded = unquote(current)
        except Exception:
            malformed = True
            break
        if decoded == current:
            break
        current = decoded
    else:
        decode_pass_limit_reached = True

    canonical_path = candidates[0] if candidates else pathname
    return {
        "canonical_path": canonical_path,
        "candidates": candidates,
        "malformed_encoding": malformed,
        "decode_pass_limit_reached": decode_pass_limit_reached,
        "raw_normalized_path": raw_normalized,
    }


def resolve_plugin_route_path_context(pathname: str) -> PluginRoutePathContext:
    """Build all security-relevant decoded path candidates for a request path."""
    canonical = _canonicalize_path_for_security(pathname)
    return PluginRoutePathContext(
        pathname=pathname,
        canonical_path=canonical["canonical_path"],
        candidates=canonical["candidates"],
        malformed_encoding=canonical["malformed_encoding"],
        decode_pass_limit_reached=canonical["decode_pass_limit_reached"],
        raw_normalized_path=canonical["raw_normalized_path"],
    )
