"""Google Meet plugin module implements calendar behavior."""

from __future__ import annotations

import datetime as _dt
import math
import re
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

from openclaw.plugin_sdk.provider_http import default_fetch_fn
from openclaw_extensions.google_meet.src.google_api_errors import google_api_error

GOOGLE_CALENDAR_API_BASE_URL = "https://www.googleapis.com/calendar/v3"
GOOGLE_CALENDAR_API_HOST = "www.googleapis.com"
GOOGLE_MEET_URL_HOST = "meet.google.com"
GOOGLE_CALENDAR_EVENTS_SCOPE = "https://www.googleapis.com/auth/calendar.events.readonly"

_MEET_URL_RE = re.compile(r"https://meet\.google\.com/[a-z0-9-]+", re.IGNORECASE)


def _append_query(url: str, query: dict[str, Any]) -> str:
    parsed = urlparse(url)
    existing = dict(__import__("urllib.parse").parse_qsl(parsed.query))
    for key, value in query.items():
        if value is not None:
            existing[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(existing)))


def _is_google_meet_uri(value: str | None) -> bool:
    if not value or not value.strip():
        return False
    try:
        return urlparse(value).hostname == GOOGLE_MEET_URL_HOST
    except Exception:
        return False


def _extract_google_meet_uri_from_text(value: str | None) -> str | None:
    if not value:
        return None
    match = _MEET_URL_RE.search(value)
    return match.group(0) if match else None


def extract_google_meet_uri_from_calendar_event(event: dict[str, Any]) -> str | None:
    if _is_google_meet_uri(event.get("hangoutLink")):
        return event.get("hangoutLink")
    conference_data = event.get("conferenceData") or {}
    entry_points = conference_data.get("entryPoints") or []
    if isinstance(entry_points, list):
        video_entry = next(
            (
                entry
                for entry in entry_points
                if isinstance(entry, dict)
                and entry.get("entryPointType") == "video"
                and _is_google_meet_uri(entry.get("uri"))
            ),
            None,
        )
        if video_entry and video_entry.get("uri"):
            return video_entry.get("uri")
        meet_entry = next(
            (
                entry
                for entry in entry_points
                if isinstance(entry, dict) and _is_google_meet_uri(entry.get("uri"))
            ),
            None,
        )
        if meet_entry and meet_entry.get("uri"):
            return meet_entry.get("uri")
    return _extract_google_meet_uri_from_text(event.get("location")) or _extract_google_meet_uri_from_text(
        event.get("description")
    )


def build_google_meet_calendar_day_window(now: _dt.datetime | None = None) -> dict[str, str]:
    now = now or _dt.datetime.now(_dt.timezone.utc)
    start = _dt.datetime(now.year, now.month, now.day, tzinfo=now.tzinfo)
    end = start + _dt.timedelta(days=1)
    return {"timeMin": start.isoformat(), "timeMax": end.isoformat()}


def _parse_calendar_event_time(value: dict[str, Any] | None) -> int | None:
    if not isinstance(value, dict):
        return None
    raw = value.get("dateTime") or value.get("date")
    if not raw or not isinstance(raw, str):
        return None
    parsed = _parse_iso_to_ms(raw)
    return parsed if parsed is not None and math.isfinite(parsed) else None


def _parse_iso_to_ms(raw: str) -> int | None:
    try:
        normalized = raw.replace("Z", "+00:00")
        parsed = _dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        return int(parsed.timestamp() * 1000)
    except Exception:
        try:
            parsed = _dt.date.fromisoformat(raw)
            return int(_dt.datetime(parsed.year, parsed.month, parsed.day, tzinfo=_dt.timezone.utc).timestamp() * 1000)
        except Exception:
            return None


def _rank_calendar_event(event: dict[str, Any], now_ms: int) -> float:
    start_ms = _parse_calendar_event_time(event.get("start")) or math.inf
    end_ms = _parse_calendar_event_time(event.get("end")) or start_ms
    if start_ms <= now_ms and end_ms >= now_ms:
        return 0
    if start_ms > now_ms:
        return start_ms - now_ms
    return now_ms - start_ms + 30 * 24 * 60 * 60 * 1000


def _choose_best_meet_calendar_event(events: list[dict[str, Any]], now: _dt.datetime) -> dict[str, Any] | None:
    now_ms = int(now.timestamp() * 1000)
    selected: dict[str, Any] | None = None
    selected_rank = math.inf
    for event in events:
        if event.get("status") == "cancelled" or not extract_google_meet_uri_from_calendar_event(event):
            continue
        rank = _rank_calendar_event(event, now_ms)
        if selected is None or rank < selected_rank:
            selected = event
            selected_rank = rank
    return selected


async def _fetch_google_calendar_events(params: dict[str, Any]) -> dict[str, Any]:
    calendar_id = (params.get("calendarId") or "").strip() or "primary"
    now = params.get("now") or _dt.datetime.now(_dt.timezone.utc)
    default_time_max = now + _dt.timedelta(days=7)
    url = _append_query(
        f"{GOOGLE_CALENDAR_API_BASE_URL}/calendars/{quote(calendar_id, safe='')}/events",
        {
            "maxResults": params.get("maxResults", 50),
            "orderBy": "startTime",
            "q": (params.get("eventQuery") or "").strip() or None,
            "showDeleted": False,
            "singleEvents": True,
            "timeMin": params.get("timeMin") or now.isoformat(),
            "timeMax": params.get("timeMax") or default_time_max.isoformat(),
        },
    )
    response = await default_fetch_fn(
        url,
        {
            "headers": {
                "Authorization": f"Bearer {params['accessToken']}",
                "Accept": "application/json",
            }
        },
    )
    try:
        if not getattr(response, "ok", False):
            raise await google_api_error(
                {
                    "response": response,
                    "prefix": "Google Calendar events.list",
                    "scopes": [GOOGLE_CALENDAR_EVENTS_SCOPE],
                }
            )
        payload = await response.json()
        if not isinstance(payload, dict):
            raise TypeError("Google Calendar events.list response was invalid")
        items = payload.get("items")
        if items is not None and not isinstance(items, list):
            raise Exception("Google Calendar events.list response had non-array items")
        return {"calendarId": calendar_id, "events": items or [], "now": now}
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()


async def list_google_meet_calendar_events(params: dict[str, Any]) -> dict[str, Any]:
    fetched = await _fetch_google_calendar_events(params)
    events = fetched["events"]
    now = fetched["now"]
    best = _choose_best_meet_calendar_event(events, now)
    mapped = []
    for event in events:
        meeting_uri = extract_google_meet_uri_from_calendar_event(event)
        if meeting_uri:
            mapped.append({"event": event, "meetingUri": meeting_uri, "selected": event is best})
    return {"calendarId": fetched["calendarId"], "events": mapped}


async def find_google_meet_calendar_event(params: dict[str, Any]) -> dict[str, Any]:
    result = await list_google_meet_calendar_events(params)
    events = result["events"]
    selected = next((event for event in events if event.get("selected")), None) or (
        events[0] if events else None
    )
    if not selected:
        raise Exception("No Google Calendar event with a Google Meet link matched the query")
    return {
        "calendarId": result["calendarId"],
        "event": selected["event"],
        "meetingUri": selected["meetingUri"],
    }
