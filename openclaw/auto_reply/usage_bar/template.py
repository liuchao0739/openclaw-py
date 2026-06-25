"""Usage bar template rendering."""

from __future__ import annotations

from typing import Any

from openclaw.auto_reply.usage_bar.translator import (
    DEFAULT_USAGE_BAR_TEMPLATE,
    UsageBarTemplate,
    translate_usage_contract,
)


def render_usage_bar(
    contract: dict[str, Any],
    template: UsageBarTemplate | None = None,
) -> str:
    """Render a usage bar string from a usage contract."""
    return translate_usage_contract(contract, template or DEFAULT_USAGE_BAR_TEMPLATE)


def render_usage_bar_line(
    contract: dict[str, Any],
    template: UsageBarTemplate | None = None,
) -> str:
    """Render a single-line usage bar with prefix."""
    text = render_usage_bar(contract, template)
    return f"📊 {text}" if text else ""
