"""Google Meet plugin module implements drive behavior."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

from openclaw.plugin_sdk.provider_http import default_fetch_fn
from openclaw_extensions.google_meet.src.google_api_errors import google_api_error

GOOGLE_DRIVE_API_BASE_URL = "https://www.googleapis.com/drive/v3"
GOOGLE_DRIVE_API_HOST = "www.googleapis.com"
GOOGLE_DRIVE_MEET_SCOPE = "https://www.googleapis.com/auth/drive.meet.readonly"
TEXT_PLAIN_MIME = "text/plain"

_HTTP_URL_RE = re.compile(r"^https?://", re.IGNORECASE)


def _append_query(url: str, query: dict[str, str | None]) -> str:
    parsed = urlparse(url)
    existing = dict(__import__("urllib.parse").parse_qsl(parsed.query))
    for key, value in query.items():
        if value is not None:
            existing[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(existing)))


def extract_google_drive_document_id(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    if not trimmed:
        return None
    if _HTTP_URL_RE.match(trimmed):
        try:
            url = urlparse(trimmed)
            document_match = re.search(r"/document/d/([^/]+)", url.path)
            return document_match.group(1) if document_match else None
        except Exception:
            return None
    segments = [segment for segment in trimmed.split("/") if segment]
    return segments[-1] if segments else None


async def export_google_drive_document_text(params: dict[str, Any]) -> str:
    url = _append_query(
        f"{GOOGLE_DRIVE_API_BASE_URL}/files/{quote(params['documentId'], safe='')}/export",
        {"mimeType": TEXT_PLAIN_MIME},
    )
    response = await default_fetch_fn(
        url,
        {
            "headers": {
                "Authorization": f"Bearer {params['accessToken']}",
                "Accept": TEXT_PLAIN_MIME,
            }
        },
    )
    try:
        if not getattr(response, "ok", False):
            raise await google_api_error(
                {
                    "response": response,
                    "prefix": "Google Drive files.export",
                    "scopes": [GOOGLE_DRIVE_MEET_SCOPE],
                }
            )
        return await read_response_text_limited(response, GOOGLE_DRIVE_EXPORT_TEXT_LIMIT_BYTES)
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()
