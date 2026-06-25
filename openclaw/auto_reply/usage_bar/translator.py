"""Usage bar translator — converts usage contracts to display text."""

from __future__ import annotations

from typing import Any, TypedDict


class UsageBarTemplate(TypedDict, total=False):
    schema: str
    showModel: bool
    showProvider: bool
    showUsage: bool
    showContext: bool
    showCost: bool
    showTiming: bool
    showIdentity: bool
    format: str


DEFAULT_USAGE_BAR_TEMPLATE: UsageBarTemplate = {
    "schema": "openclaw.usageBar.v1",
    "showModel": True,
    "showProvider": False,
    "showUsage": True,
    "showContext": True,
    "showCost": False,
    "showTiming": False,
    "showIdentity": False,
    "format": "compact",
}


def translate_usage_contract(
    contract: dict[str, Any],
    template: UsageBarTemplate | None = None,
) -> str:
    """Translate a usage contract into a display string using a template."""
    tmpl = template or DEFAULT_USAGE_BAR_TEMPLATE
    parts: list[str] = []

    # Model
    if tmpl.get("showModel", True):
        model = contract.get("model", {})
        model_id = model.get("display_name") or model.get("id")
        if model_id:
            parts.append(model_id)
        if tmpl.get("showProvider", False):
            provider = model.get("provider")
            if provider:
                parts.append(f"({provider})")

    # Usage
    if tmpl.get("showUsage", True):
        usage = contract.get("usage", {})
        if usage.get("has_tokens"):
            tokens: list[str] = []
            if usage.get("input_tokens") is not None:
                tokens.append(f"in:{_format_num(usage['input_tokens'])}")
            if usage.get("output_tokens") is not None:
                tokens.append(f"out:{_format_num(usage['output_tokens'])}")
            if usage.get("cache_read_tokens") is not None:
                tokens.append(f"cache:{_format_num(usage['cache_read_tokens'])}")
            if not tokens and usage.get("total_tokens") is not None:
                tokens.append(f"total:{_format_num(usage['total_tokens'])}")
            if usage.get("cache_hit_pct") is not None:
                tokens.append(f"hit:{usage['cache_hit_pct']}%")
            if tokens:
                parts.append(" ".join(tokens))

    # Context
    if tmpl.get("showContext", True):
        context = contract.get("context", {})
        if context.get("pct_used") is not None:
            parts.append(f"ctx:{context['pct_used']}%")

    # Cost
    if tmpl.get("showCost", False):
        cost = contract.get("cost", {})
        if cost.get("available") and cost.get("turn_usd") is not None:
            parts.append(f"${cost['turn_usd']:.4f}")

    # Timing
    if tmpl.get("showTiming", False):
        timing = contract.get("timing", {})
        if timing.get("duration_ms") is not None:
            parts.append(f"{_format_duration(timing['duration_ms'])}")

    # Identity
    if tmpl.get("showIdentity", False):
        identity = contract.get("identity", {})
        name = identity.get("name")
        emoji = identity.get("emoji")
        if emoji:
            parts.append(emoji)
        if name:
            parts.append(name)

    return " | ".join(parts) if parts else ""


def _format_num(n: int | float) -> str:
    """Format a number with K/M suffixes."""
    if n >= 1_000_000:
        return f"{n / 1_000_000:.1f}M"
    if n >= 1_000:
        return f"{n / 1_000:.1f}K"
    return str(int(n))


def _format_duration(ms: int | float) -> str:
    """Format a duration in milliseconds."""
    if ms >= 60_000:
        return f"{ms / 60_000:.1f}min"
    if ms >= 1_000:
        return f"{ms / 1_000:.1f}s"
    return f"{int(ms)}ms"
