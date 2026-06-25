"""Shared web tool utilities.

Provides URL validation, content type helpers, and fetch result formatting
used by web-fetch, web-search, and other web-related tools.
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse

MAX_WEB_FETCH_CONTENT_CHARS = 100_000
MAX_WEB_SEARCH_RESULTS = 20

_URL_SCHEME_PATTERN = re.compile(r"^https?://", re.IGNORECASE)


def is_valid_url(url: str | None) -> bool:
    """Check if a string is a valid HTTP/HTTPS URL."""
    if not url or not isinstance(url, str):
        return False
    if not _URL_SCHEME_PATTERN.match(url):
        return False
    try:
        parsed = urlparse(url)
        return bool(parsed.hostname)
    except Exception:
        return False


def normalize_url(url: str) -> str:
    """Normalize a URL by ensuring it has a scheme."""
    if not url:
        return url
    if not _URL_SCHEME_PATTERN.match(url):
        return f"https://{url}"
    return url


def truncate_web_content(content: str, max_chars: int = MAX_WEB_FETCH_CONTENT_CHARS) -> str:
    """Truncate web content to max characters."""
    if len(content) <= max_chars:
        return content
    return content[:max_chars] + "\n\n[Content truncated]"


def format_web_fetch_result(
    url: str,
    content: str,
    *,
    title: str | None = None,
    content_type: str | None = None,
) -> dict[str, Any]:
    """Format a web fetch result for tool output."""
    text_parts = [f"URL: {url}"]
    if title:
        text_parts.append(f"Title: {title}")
    if content_type:
        text_parts.append(f"Content-Type: {content_type}")
    text_parts.append("")
    text_parts.append(truncate_web_content(content))
    return {
        "content": [{"type": "text", "text": "\n".join(text_parts)}],
    }


def format_web_search_result(results: list[dict[str, Any]]) -> dict[str, Any]:
    """Format web search results for tool output."""
    truncated = results[:MAX_WEB_SEARCH_RESULTS]
    lines: list[str] = []
    for i, result in enumerate(truncated, 1):
        title = result.get("title", "Untitled")
        url = result.get("url", "")
        snippet = result.get("snippet", "")
        lines.append(f"{i}. {title}")
        if url:
            lines.append(f"   URL: {url}")
        if snippet:
            lines.append(f"   {snippet}")
        lines.append("")

    if len(results) > MAX_WEB_SEARCH_RESULTS:
        lines.append(f"[{len(results) - MAX_WEB_SEARCH_RESULTS} more results omitted]")

    return {
        "content": [{"type": "text", "text": "\n".join(lines)}],
    }
