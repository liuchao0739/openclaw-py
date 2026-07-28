"""Entry metadata helpers resolve display names, emojis, and homepage links."""

from __future__ import annotations

from typing import Any


def resolve_emoji_and_homepage(
    metadata: dict[str, Any] | None = None,
    frontmatter: dict[str, Any] | None = None,
) -> tuple[str | None, str | None]:
    emoji = None
    homepage_raw = None
    if metadata:
        emoji = metadata.get("emoji")
        homepage_raw = metadata.get("homepage")
    if not homepage_raw and frontmatter:
        homepage_raw = frontmatter.get("homepage") or frontmatter.get("website") or frontmatter.get("url")
    homepage = homepage_raw.strip() if isinstance(homepage_raw, str) else None
    return (emoji if emoji else None, homepage if homepage else None)
