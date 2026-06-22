"""Lightweight glob pattern compile/match for agent policies."""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Literal


@dataclass(frozen=True)
class _All:
    kind: Literal["all"] = "all"


@dataclass(frozen=True)
class _Exact:
    value: str
    kind: Literal["exact"] = "exact"


@dataclass(frozen=True)
class _Regex:
    value: re.Pattern[str]
    kind: Literal["regex"] = "regex"


CompiledGlobPattern = _All | _Exact | _Regex


def _escape_regex(value: str) -> str:
    return re.escape(value)


def _compile_glob_pattern(raw: str, normalize: Callable[[str], str]) -> CompiledGlobPattern:
    normalized = normalize(raw)
    if not normalized:
        return _Exact("")
    if normalized == "*":
        return _All()
    if "*" not in normalized:
        return _Exact(normalized)
    pattern = "^" + _escape_regex(normalized).replace("\\*", ".*") + "$"
    return _Regex(re.compile(pattern))


def compile_glob_patterns(
    *,
    raw: list[str] | None,
    normalize: Callable[[str], str],
) -> list[CompiledGlobPattern]:
    if not isinstance(raw, list):
        return []
    out: list[CompiledGlobPattern] = []
    for item in raw:
        compiled = _compile_glob_pattern(item, normalize)
        if compiled.kind == "exact" and not compiled.value:
            continue
        out.append(compiled)
    return out


def matches_any_glob_pattern(value: str, patterns: list[CompiledGlobPattern]) -> bool:
    for pattern in patterns:
        if pattern.kind == "all":
            return True
        if pattern.kind == "exact" and value == pattern.value:
            return True
        if pattern.kind == "regex" and pattern.value.match(value):
            return True
    return False