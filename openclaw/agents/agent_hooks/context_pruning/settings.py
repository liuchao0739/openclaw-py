"""Config normalization for cache-TTL based context pruning."""

from __future__ import annotations

import copy
import re
from dataclasses import dataclass, field
from typing import Any, Literal

ContextPruningMode = Literal["off", "cache-ttl"]


@dataclass
class ContextPruningToolMatch:
    allow: list[str] | None = None
    deny: list[str] | None = None


@dataclass
class SoftTrimSettings:
    max_chars: int = 4_000
    head_chars: int = 1_500
    tail_chars: int = 1_500


@dataclass
class HardClearSettings:
    enabled: bool = True
    placeholder: str = "[Old tool result content cleared]"


@dataclass
class EffectiveContextPruningSettings:
    mode: Literal["cache-ttl"]
    ttl_ms: int
    keep_last_assistants: int
    soft_trim_ratio: float
    hard_clear_ratio: float
    min_prunable_tool_chars: int
    tools: ContextPruningToolMatch
    soft_trim: SoftTrimSettings
    hard_clear: HardClearSettings


DEFAULT_CONTEXT_PRUNING_SETTINGS = EffectiveContextPruningSettings(
    mode="cache-ttl",
    ttl_ms=5 * 60 * 1000,
    keep_last_assistants=3,
    soft_trim_ratio=0.3,
    hard_clear_ratio=0.5,
    min_prunable_tool_chars=50_000,
    tools=ContextPruningToolMatch(),
    soft_trim=SoftTrimSettings(),
    hard_clear=HardClearSettings(),
)


_DURATION_RE = re.compile(
    r"^(\d+(?:\.\d+)?)\s*(ms|s|m|h|d)?$",
    re.IGNORECASE,
)


def parse_duration_ms(value: str, *, default_unit: str = "m") -> int:
    trimmed = value.strip()
    match = _DURATION_RE.match(trimmed)
    if not match:
        raise ValueError(f"invalid duration: {value}")
    amount = float(match.group(1))
    unit = (match.group(2) or default_unit).lower()
    multipliers = {"ms": 1, "s": 1000, "m": 60_000, "h": 3_600_000, "d": 86_400_000}
    if unit not in multipliers:
        raise ValueError(f"unknown unit: {unit}")
    return int(amount * multipliers[unit])


def compute_effective_settings(raw: Any) -> EffectiveContextPruningSettings | None:
    if not raw or not isinstance(raw, dict):
        return None
    if raw.get("mode") != "cache-ttl":
        return None

    base = DEFAULT_CONTEXT_PRUNING_SETTINGS
    s = EffectiveContextPruningSettings(
        mode="cache-ttl",
        ttl_ms=base.ttl_ms,
        keep_last_assistants=base.keep_last_assistants,
        soft_trim_ratio=base.soft_trim_ratio,
        hard_clear_ratio=base.hard_clear_ratio,
        min_prunable_tool_chars=base.min_prunable_tool_chars,
        tools=ContextPruningToolMatch(
            allow=copy.deepcopy(base.tools.allow),
            deny=copy.deepcopy(base.tools.deny),
        ),
        soft_trim=SoftTrimSettings(
            max_chars=base.soft_trim.max_chars,
            head_chars=base.soft_trim.head_chars,
            tail_chars=base.soft_trim.tail_chars,
        ),
        hard_clear=HardClearSettings(
            enabled=base.hard_clear.enabled,
            placeholder=base.hard_clear.placeholder,
        ),
    )

    ttl = raw.get("ttl")
    if isinstance(ttl, str):
        try:
            s.ttl_ms = parse_duration_ms(ttl, default_unit="m")
        except ValueError:
            pass

    kla = raw.get("keepLastAssistants")
    if isinstance(kla, (int, float)) and kla == kla:  # finite
        s.keep_last_assistants = max(0, int(kla))

    for key, attr in (
        ("softTrimRatio", "soft_trim_ratio"),
        ("hardClearRatio", "hard_clear_ratio"),
    ):
        val = raw.get(key)
        if isinstance(val, (int, float)) and val == val:
            setattr(s, attr, min(1.0, max(0.0, float(val))))

    mptc = raw.get("minPrunableToolChars")
    if isinstance(mptc, (int, float)) and mptc == mptc:
        s.min_prunable_tool_chars = max(0, int(mptc))

    tools = raw.get("tools")
    if isinstance(tools, dict):
        allow = tools.get("allow")
        deny = tools.get("deny")
        s.tools = ContextPruningToolMatch(
            allow=list(allow) if isinstance(allow, list) else None,
            deny=list(deny) if isinstance(deny, list) else None,
        )

    soft_trim = raw.get("softTrim")
    if isinstance(soft_trim, dict):
        for src, dst in (
            ("maxChars", "max_chars"),
            ("headChars", "head_chars"),
            ("tailChars", "tail_chars"),
        ):
            val = soft_trim.get(src)
            if isinstance(val, (int, float)) and val == val:
                setattr(s.soft_trim, dst, max(0, int(val)))

    hard_clear = raw.get("hardClear")
    if isinstance(hard_clear, dict):
        enabled = hard_clear.get("enabled")
        if isinstance(enabled, bool):
            s.hard_clear.enabled = enabled
        placeholder = hard_clear.get("placeholder")
        if isinstance(placeholder, str) and placeholder.strip():
            s.hard_clear.placeholder = placeholder.strip()

    return s