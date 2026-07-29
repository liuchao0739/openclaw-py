"""Google Meet plugin module implements meet behavior."""

from __future__ import annotations

import datetime as _dt
import json
import math
import re
from typing import Any
from urllib.parse import quote, urlencode, urlparse, urlunparse

from openclaw.packages.normalization_core import normalize_optional_string, unique_strings
from openclaw.plugin_sdk.provider_http import default_fetch_fn
from openclaw_extensions.google_meet.src.drive import (
    export_google_drive_document_text,
    extract_google_drive_document_id,
)
from openclaw_extensions.google_meet.src.google_api_errors import google_api_error

GOOGLE_MEET_API_ORIGIN = "https://meet.googleapis.com"
GOOGLE_MEET_API_BASE_URL = f"{GOOGLE_MEET_API_ORIGIN}/v2"
GOOGLE_MEET_URL_HOST = "meet.google.com"
GOOGLE_MEET_API_HOST = "meet.googleapis.com"
GOOGLE_MEET_MEDIA_SCOPE = "https://www.googleapis.com/auth/meetings.conference.media.readonly"
GOOGLE_MEET_SPACE_SCOPE = "https://www.googleapis.com/auth/meetings.space.readonly"
GOOGLE_MEET_SPACE_CREATED_SCOPE = "https://www.googleapis.com/auth/meetings.space.created"
GOOGLE_MEET_SPACE_SETTINGS_SCOPE = "https://www.googleapis.com/auth/meetings.space.settings"

_MEETING_CODE_PATH_RE = re.compile(r"^/[a-z]{3}-[a-z]{4}-[a-z]{3}(?:$|[/?#])", re.IGNORECASE)


def normalize_google_meet_space_name(input_value: str) -> str:
    trimmed = input_value.strip()
    if not trimmed:
        raise ValueError("Meeting input is required")
    if trimmed.startswith("spaces/"):
        suffix = trimmed[len("spaces/"):].strip()
        if not suffix:
            raise ValueError("spaces/ input must include a meeting code or space id")
        return f"spaces/{suffix}"
    if re.match(r"^https?://", trimmed, re.IGNORECASE):
        url = urlparse(trimmed)
        if url.hostname != GOOGLE_MEET_URL_HOST:
            raise ValueError(f"Expected a {GOOGLE_MEET_URL_HOST} URL, received {url.hostname}")
        first_segment = next(
            (segment.strip() for segment in url.path.split("/") if segment.strip()),
            None,
        )
        if not first_segment:
            raise ValueError("Google Meet URL did not include a meeting code")
        return f"spaces/{first_segment}"
    return f"spaces/{trimmed}"


def _encode_space_name_for_path(name: str) -> str:
    return "/".join(quote(part, safe="") for part in name.split("/"))


def _encode_resource_name_for_path(name: str) -> str:
    trimmed = name.strip()
    if not trimmed:
        raise ValueError("Google Meet resource name is required")
    return "/".join(quote(part, safe="") for part in trimmed.split("/"))


def _normalize_conference_record_name(input_value: str) -> str:
    trimmed = input_value.strip()
    if not trimmed:
        raise ValueError("Conference record is required")
    return trimmed if trimmed.startswith("conferenceRecords/") else f"conferenceRecords/{trimmed}"


def _append_query(
    url: str,
    query: dict[str, str | int | float | bool | None] | None,
) -> str:
    if not query:
        return url
    parsed = urlparse(url)
    existing = dict(__import__("urllib.parse").parse_qsl(parsed.query))
    for key, value in query.items():
        if value is not None:
            existing[key] = str(value)
    return urlunparse(parsed._replace(query=urlencode(existing)))


def _assert_resource_array(
    value: Any,
    key: str,
    context: str,
) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list):
        raise ValueError(f"Google Meet {context} response had non-array {key}")
    for resource in value:
        if not isinstance(resource, dict) or not str(resource.get("name", "")).strip():
            raise ValueError(f"Google Meet {context} response included a resource without name")
    return value


def _get_error_message(error: Any) -> str:
    return str(error) if isinstance(error, BaseException) else str(error)


async def _fetch_google_meet_json(params: dict[str, Any]) -> Any:
    url = _append_query(
        f"{GOOGLE_MEET_API_BASE_URL}/{params['path']}",
        params.get("query"),
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
                    "prefix": params["errorPrefix"],
                    "scopes": [GOOGLE_MEET_MEDIA_SCOPE],
                }
            )
        return await response.json()
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()


async def _list_google_meet_collection(params: dict[str, Any]) -> list[dict[str, Any]]:
    items: list[dict[str, Any]] = []
    page_token: str | None = None
    while True:
        query = dict(params.get("query") or {})
        if page_token:
            query["pageToken"] = page_token
        payload = await _fetch_google_meet_json(
            {
                "accessToken": params["accessToken"],
                "path": params["path"],
                "query": query,
                "auditContext": params["auditContext"],
                "errorPrefix": params["errorPrefix"],
            }
        )
        if not isinstance(payload, dict):
            payload = {}
        page_items = _assert_resource_array(
            payload.get(params["collectionKey"]),
            params["collectionKey"],
            params["errorPrefix"],
        )
        max_items = params.get("maxItems")
        if isinstance(max_items, int):
            remaining = max(max_items - len(items), 0)
            items.extend(page_items[:remaining])
            if len(items) >= max_items:
                break
        else:
            items.extend(page_items)
        next_page_token = payload.get("nextPageToken")
        page_token = next_page_token if isinstance(next_page_token, str) and next_page_token else None
        if not page_token:
            break
    return items


async def fetch_google_meet_space(params: dict[str, Any]) -> dict[str, Any]:
    name = normalize_google_meet_space_name(params["meeting"])
    response = await default_fetch_fn(
        f"{GOOGLE_MEET_API_BASE_URL}/{_encode_space_name_for_path(name)}",
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
                    "prefix": "Google Meet spaces.get",
                    "scopes": [GOOGLE_MEET_SPACE_SCOPE],
                }
            )
        payload = await response.json()
        if not isinstance(payload, dict) or not str(payload.get("name", "")).strip():
            raise ValueError("Google Meet spaces.get response was missing name")
        return payload
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()


async def create_google_meet_space(params: dict[str, Any]) -> dict[str, Any]:
    config = params.get("config")
    body = (
        json.dumps({"config": config})
        if isinstance(config, dict) and config
        else "{}"
    )
    response = await default_fetch_fn(
        f"{GOOGLE_MEET_API_BASE_URL}/spaces",
        {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {params['accessToken']}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "body": body,
        },
    )
    try:
        if not getattr(response, "ok", False):
            scopes = (
                [GOOGLE_MEET_SPACE_CREATED_SCOPE, GOOGLE_MEET_SPACE_SETTINGS_SCOPE]
                if isinstance(config, dict) and config
                else [GOOGLE_MEET_SPACE_CREATED_SCOPE]
            )
            raise await google_api_error(
                {
                    "response": response,
                    "prefix": "Google Meet spaces.create",
                    "scopes": scopes,
                }
            )
        payload = await response.json()
        if not isinstance(payload, dict) or not str(payload.get("name", "")).strip():
            raise ValueError("Google Meet spaces.create response was missing name")
        meeting_uri = normalize_optional_string(payload.get("meetingUri"))
        if not meeting_uri:
            raise ValueError("Google Meet spaces.create response was missing meetingUri")
        return {"space": payload, "meetingUri": meeting_uri}
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()


async def end_google_meet_active_conference(params: dict[str, Any]) -> dict[str, Any]:
    resolved = await fetch_google_meet_space(
        {
            "accessToken": params["accessToken"],
            "meeting": params["meeting"],
        }
    )
    space = resolved["name"]
    response = await default_fetch_fn(
        f"{GOOGLE_MEET_API_BASE_URL}/{_encode_space_name_for_path(space)}:endActiveConference",
        {
            "method": "POST",
            "headers": {
                "Authorization": f"Bearer {params['accessToken']}",
                "Accept": "application/json",
                "Content-Type": "application/json",
            },
            "body": "{}",
        },
    )
    try:
        if not getattr(response, "ok", False):
            raise await google_api_error(
                {
                    "response": response,
                    "prefix": "Google Meet spaces.endActiveConference",
                    "scopes": [GOOGLE_MEET_SPACE_CREATED_SCOPE],
                }
            )
        return {"space": space, "ended": True}
    finally:
        release = getattr(response, "release", None)
        if callable(release):
            await release()


async def _fetch_google_meet_conference_record(params: dict[str, Any]) -> dict[str, Any]:
    name = _normalize_conference_record_name(params["conferenceRecord"])
    payload = await _fetch_google_meet_json(
        {
            "accessToken": params["accessToken"],
            "path": _encode_resource_name_for_path(name),
            "auditContext": "google-meet.conferenceRecords.get",
            "errorPrefix": "Google Meet conferenceRecords.get",
        }
    )
    if not isinstance(payload, dict) or not str(payload.get("name", "")).strip():
        raise ValueError("Google Meet conferenceRecords.get response was missing name")
    return payload


async def _list_google_meet_conference_records(params: dict[str, Any]) -> list[dict[str, Any]]:
    meeting = params.get("meeting")
    filter_value = (
        f'space.name = "{normalize_google_meet_space_name(meeting)}"'
        if meeting and meeting.strip()
        else None
    )
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": "conferenceRecords",
            "collectionKey": "conferenceRecords",
            "query": {
                "pageSize": params.get("pageSize"),
                "filter": filter_value,
            },
            "maxItems": params.get("maxItems"),
            "auditContext": "google-meet.conferenceRecords.list",
            "errorPrefix": "Google Meet conferenceRecords.list",
        }
    )


async def fetch_latest_google_meet_conference_record(params: dict[str, Any]) -> dict[str, Any]:
    space = await fetch_google_meet_space(
        {
            "accessToken": params["accessToken"],
            "meeting": params["meeting"],
        }
    )
    records = await _list_google_meet_conference_records(
        {
            "accessToken": params["accessToken"],
            "meeting": space["name"],
            "pageSize": 1,
            "maxItems": 1,
        }
    )
    result: dict[str, Any] = {
        "input": params["meeting"],
        "space": space,
    }
    if records:
        result["conferenceRecord"] = records[0]
    return result


async def _list_google_meet_participants(params: dict[str, Any]) -> list[dict[str, Any]]:
    parent = _normalize_conference_record_name(params["conferenceRecord"])
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(parent)}/participants",
            "collectionKey": "participants",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.participants.list",
            "errorPrefix": "Google Meet conferenceRecords.participants.list",
        }
    )


async def _list_google_meet_participant_sessions(params: dict[str, Any]) -> list[dict[str, Any]]:
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(params['participant'])}/participantSessions",
            "collectionKey": "participantSessions",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.participants.participantSessions.list",
            "errorPrefix": "Google Meet conferenceRecords.participants.participantSessions.list",
        }
    )


async def _list_google_meet_recordings(params: dict[str, Any]) -> list[dict[str, Any]]:
    parent = _normalize_conference_record_name(params["conferenceRecord"])
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(parent)}/recordings",
            "collectionKey": "recordings",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.recordings.list",
            "errorPrefix": "Google Meet conferenceRecords.recordings.list",
        }
    )


async def _list_google_meet_transcripts(params: dict[str, Any]) -> list[dict[str, Any]]:
    parent = _normalize_conference_record_name(params["conferenceRecord"])
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(parent)}/transcripts",
            "collectionKey": "transcripts",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.transcripts.list",
            "errorPrefix": "Google Meet conferenceRecords.transcripts.list",
        }
    )


async def _list_google_meet_transcript_entries(params: dict[str, Any]) -> list[dict[str, Any]]:
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(params['transcript'])}/entries",
            "collectionKey": "transcriptEntries",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.transcripts.entries.list",
            "errorPrefix": "Google Meet conferenceRecords.transcripts.entries.list",
        }
    )


async def _list_google_meet_smart_notes(params: dict[str, Any]) -> list[dict[str, Any]]:
    parent = _normalize_conference_record_name(params["conferenceRecord"])
    return await _list_google_meet_collection(
        {
            "accessToken": params["accessToken"],
            "path": f"{_encode_resource_name_for_path(parent)}/smartNotes",
            "collectionKey": "smartNotes",
            "query": {"pageSize": params.get("pageSize")},
            "auditContext": "google-meet.conferenceRecords.smartNotes.list",
            "errorPrefix": "Google Meet conferenceRecords.smartNotes.list",
        }
    )


def _get_participant_display_name(participant: dict[str, Any]) -> str | None:
    signedin = participant.get("signedinUser") or {}
    anonymous = participant.get("anonymousUser") or {}
    phone = participant.get("phoneUser") or {}
    return (
        signedin.get("displayName")
        if isinstance(signedin, dict)
        else None
    ) or (
        anonymous.get("displayName")
        if isinstance(anonymous, dict)
        else None
    ) or (
        phone.get("displayName")
        if isinstance(phone, dict)
        else None
    )


def _get_participant_user(participant: dict[str, Any]) -> str | None:
    signedin = participant.get("signedinUser")
    if isinstance(signedin, dict):
        return signedin.get("user")
    return None


def _get_docs_destination_document_id(destination: dict[str, Any] | None) -> str | None:
    if not isinstance(destination, dict):
        return None
    return (
        extract_google_drive_document_id(destination.get("document"))
        or extract_google_drive_document_id(destination.get("documentId"))
        or extract_google_drive_document_id(destination.get("file"))
    )


async def _attach_document_text(params: dict[str, Any]) -> dict[str, Any]:
    resource = params["resource"]
    if not isinstance(resource, dict):
        return resource
    document_id = _get_docs_destination_document_id(resource.get("docsDestination"))
    if not document_id:
        return resource
    try:
        document_text = await export_google_drive_document_text(
            {
                "accessToken": params["accessToken"],
                "documentId": document_id,
            }
        )
        return {**resource, "documentText": document_text}
    except Exception as error:
        return {**resource, "documentTextError": _get_error_message(error)}


def _parse_google_meet_timestamp(value: str | None) -> int | None:
    if not value or not value.strip():
        return None
    try:
        normalized = value.replace("Z", "+00:00")
        parsed = _dt.datetime.fromisoformat(normalized)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=_dt.timezone.utc)
        return int(parsed.timestamp() * 1000)
    except Exception:
        try:
            parsed_date = _dt.date.fromisoformat(value)
            return int(
                _dt.datetime(
                    parsed_date.year,
                    parsed_date.month,
                    parsed_date.day,
                    tzinfo=_dt.timezone.utc,
                ).timestamp()
                * 1000
            )
        except Exception:
            return None


def _iso_from_ms(value: int | None) -> str | None:
    if value is None or not math.isfinite(value):
        return None
    return _dt.datetime.fromtimestamp(value / 1000, tz=_dt.timezone.utc).isoformat()


def _min_timestamp(values: list[str | None]) -> str | None:
    parsed = [
        ms
        for ms in (_parse_google_meet_timestamp(v) for v in values)
        if ms is not None
    ]
    return _iso_from_ms(min(parsed)) if parsed else None


def _max_timestamp(values: list[str | None]) -> str | None:
    parsed = [
        ms
        for ms in (_parse_google_meet_timestamp(v) for v in values)
        if ms is not None
    ]
    return _iso_from_ms(max(parsed)) if parsed else None


def _sum_session_duration_ms(
    sessions: list[dict[str, Any]],
    fallback_start: str | None,
    fallback_end: str | None,
) -> int | None:
    session_total = 0
    for session in sessions:
        start_ms = _parse_google_meet_timestamp(session.get("startTime"))
        end_ms = _parse_google_meet_timestamp(session.get("endTime"))
        if start_ms is not None and end_ms is not None and end_ms > start_ms:
            session_total += end_ms - start_ms
    if session_total > 0:
        return session_total
    start_ms = _parse_google_meet_timestamp(fallback_start)
    end_ms = _parse_google_meet_timestamp(fallback_end)
    if start_ms is not None and end_ms is not None and end_ms > start_ms:
        return end_ms - start_ms
    return None


def _attendance_merge_key(row: dict[str, Any]) -> str:
    raw = row.get("user") or row.get("displayName") or row.get("participant") or ""
    return str(raw).strip().lower()


def _sort_sessions(sessions: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return sorted(
        sessions,
        key=lambda session: _parse_google_meet_timestamp(session.get("startTime")) or 0,
    )


def _decorate_attendance_row(
    row: dict[str, Any],
    conference_record: dict[str, Any],
    params: dict[str, Any],
) -> dict[str, Any]:
    sessions = _sort_sessions(row.get("sessions") or [])
    first_join_time = _min_timestamp(
        [row.get("earliestStartTime")] + [s.get("startTime") for s in sessions]
    )
    last_leave_time = _max_timestamp(
        [row.get("latestEndTime")] + [s.get("endTime") for s in sessions]
    )
    duration_ms = _sum_session_duration_ms(sessions, first_join_time, last_leave_time)
    conference_start_ms = _parse_google_meet_timestamp(conference_record.get("startTime"))
    conference_end_ms = _parse_google_meet_timestamp(conference_record.get("endTime"))
    first_join_ms = _parse_google_meet_timestamp(first_join_time)
    last_leave_ms = _parse_google_meet_timestamp(last_leave_time)
    late_grace_ms = (params.get("lateAfterMinutes") or 5) * 60_000
    early_grace_ms = (params.get("earlyBeforeMinutes") or 5) * 60_000
    late_by_ms = (
        max(first_join_ms - conference_start_ms, 0)
        if conference_start_ms is not None and first_join_ms is not None
        else None
    )
    early_leave_by_ms = (
        max(conference_end_ms - last_leave_ms, 0)
        if conference_end_ms is not None and last_leave_ms is not None
        else None
    )
    decorated = {
        **row,
        "sessions": sessions,
        "participants": row.get("participants") or [row.get("participant")],
    }
    decorated["earliestStartTime"] = first_join_time or row.get("earliestStartTime")
    decorated["latestEndTime"] = last_leave_time or row.get("latestEndTime")
    if first_join_time:
        decorated["firstJoinTime"] = first_join_time
    if last_leave_time:
        decorated["lastLeaveTime"] = last_leave_time
    if duration_ms is not None:
        decorated["durationMs"] = duration_ms
    if late_by_ms is not None:
        decorated["late"] = late_by_ms > late_grace_ms
        if decorated["late"]:
            decorated["lateByMs"] = late_by_ms
    if early_leave_by_ms is not None:
        decorated["earlyLeave"] = early_leave_by_ms > early_grace_ms
        if decorated["earlyLeave"]:
            decorated["earlyLeaveByMs"] = early_leave_by_ms
    return decorated


def _merge_attendance_rows(
    rows: list[dict[str, Any]],
    conference_record: dict[str, Any],
    params: dict[str, Any],
) -> list[dict[str, Any]]:
    if params.get("mergeDuplicateParticipants") is False:
        return [_decorate_attendance_row(row, conference_record, params) for row in rows]
    grouped: dict[str, dict[str, Any]] = {}
    for row in rows:
        key = _attendance_merge_key(row)
        existing = grouped.get(key)
        if not existing:
            grouped[key] = {**row, "participants": [row.get("participant")]}
            continue
        existing["participants"] = unique_strings(
            [*(existing.get("participants") or [existing.get("participant")]), row.get("participant")]
        )
        existing.setdefault("sessions", []).extend(row.get("sessions") or [])
        if not existing.get("displayName") and row.get("displayName"):
            existing["displayName"] = row.get("displayName")
        if not existing.get("user") and row.get("user"):
            existing["user"] = row.get("user")
        existing["earliestStartTime"] = _min_timestamp(
            [existing.get("earliestStartTime"), row.get("earliestStartTime")]
        )
        existing["latestEndTime"] = _max_timestamp(
            [existing.get("latestEndTime"), row.get("latestEndTime")]
        )
    return [_decorate_attendance_row(row, conference_record, params) for row in grouped.values()]


async def _resolve_conference_record_query(params: dict[str, Any]) -> dict[str, Any]:
    conference_record_input = normalize_optional_string(params.get("conferenceRecord"))
    if conference_record_input:
        record = await _fetch_google_meet_conference_record(
            {
                "accessToken": params["accessToken"],
                "conferenceRecord": conference_record_input,
            }
        )
        return {
            "input": conference_record_input,
            "conferenceRecords": [record],
        }
    meeting = normalize_optional_string(params.get("meeting"))
    if not meeting:
        raise ValueError("Meeting input or conference record is required")
    space = await fetch_google_meet_space(
        {
            "accessToken": params["accessToken"],
            "meeting": meeting,
        }
    )
    records = await _list_google_meet_conference_records(
        {
            "accessToken": params["accessToken"],
            "meeting": space["name"],
            "pageSize": params.get("pageSize") if params.get("allConferenceRecords") else 1,
            "maxItems": None if params.get("allConferenceRecords") else 1,
        }
    )
    return {
        "input": meeting,
        "space": space,
        "conferenceRecords": records,
    }


async def fetch_google_meet_artifacts(params: dict[str, Any]) -> dict[str, Any]:
    resolved = await _resolve_conference_record_query(params)

    async def _build_artifact(conference_record: dict[str, Any]) -> dict[str, Any]:
        participants, recordings, transcripts, smart_notes_result = await _gather(
            [
                _list_google_meet_participants(
                    {
                        "accessToken": params["accessToken"],
                        "conferenceRecord": conference_record["name"],
                        "pageSize": params.get("pageSize"),
                    }
                ),
                _list_google_meet_recordings(
                    {
                        "accessToken": params["accessToken"],
                        "conferenceRecord": conference_record["name"],
                        "pageSize": params.get("pageSize"),
                    }
                ),
                _list_google_meet_transcripts(
                    {
                        "accessToken": params["accessToken"],
                        "conferenceRecord": conference_record["name"],
                        "pageSize": params.get("pageSize"),
                    }
                ),
                _list_smart_notes_safe(params, conference_record["name"]),
            ]
        )
        transcript_entries: list[dict[str, Any]] = []
        if params.get("includeTranscriptEntries") is not False:
            transcript_entries = await _gather_flat(
                transcripts,
                lambda transcript: _safe_transcript_entries(params, transcript),
            )
        transcriptsWithText = (
            await _gather_flat(
                transcripts,
                lambda transcript: _attach_document_text(
                    {"accessToken": params["accessToken"], "resource": transcript}
                ),
            )
            if params.get("includeDocumentBodies") is True
            else transcripts
        )
        smart_notes_with_text = (
            await _gather_flat(
                smart_notes_result["smartNotes"],
                lambda smart_note: _attach_document_text(
                    {"accessToken": params["accessToken"], "resource": smart_note}
                ),
            )
            if params.get("includeDocumentBodies") is True
            else smart_notes_result["smartNotes"]
        )
        result: dict[str, Any] = {
            "conferenceRecord": conference_record,
            "participants": participants,
            "recordings": recordings,
            "transcripts": transcriptsWithText,
            "transcriptEntries": transcript_entries,
            "smartNotes": smart_notes_with_text,
        }
        if smart_notes_result.get("smartNotesError"):
            result["smartNotesError"] = smart_notes_result["smartNotesError"]
        return result

    artifacts = await _gather_flat(resolved["conferenceRecords"], _build_artifact)
    return {
        "input": resolved.get("input"),
        "space": resolved.get("space"),
        "conferenceRecords": resolved["conferenceRecords"],
        "artifacts": artifacts,
    }


async def _list_smart_notes_safe(params: dict[str, Any], conference_record_name: str) -> dict[str, Any]:
    try:
        smart_notes = await _list_google_meet_smart_notes(
            {
                "accessToken": params["accessToken"],
                "conferenceRecord": conference_record_name,
                "pageSize": params.get("pageSize"),
            }
        )
        return {"smartNotes": smart_notes}
    except Exception as error:
        return {"smartNotes": [], "smartNotesError": _get_error_message(error)}


async def _safe_transcript_entries(params: dict[str, Any], transcript: dict[str, Any]) -> dict[str, Any]:
    try:
        entries = await _list_google_meet_transcript_entries(
            {
                "accessToken": params["accessToken"],
                "transcript": transcript["name"],
                "pageSize": params.get("pageSize"),
            }
        )
        return {"transcript": transcript["name"], "entries": entries}
    except Exception as error:
        return {
            "transcript": transcript["name"],
            "entries": [],
            "entriesError": _get_error_message(error),
        }


async def fetch_google_meet_attendance(params: dict[str, Any]) -> dict[str, Any]:
    resolved = await _resolve_conference_record_query(params)

    async def _build_attendance(conference_record: dict[str, Any]) -> list[dict[str, Any]]:
        participants = await _list_google_meet_participants(
            {
                "accessToken": params["accessToken"],
                "conferenceRecord": conference_record["name"],
                "pageSize": params.get("pageSize"),
            }
        )

        async def _build_row(participant: dict[str, Any]) -> dict[str, Any]:
            sessions = await _list_google_meet_participant_sessions(
                {
                    "accessToken": params["accessToken"],
                    "participant": participant["name"],
                    "pageSize": params.get("pageSize"),
                }
            )
            return {
                "conferenceRecord": conference_record["name"],
                "participant": participant["name"],
                "displayName": _get_participant_display_name(participant),
                "user": _get_participant_user(participant),
                "earliestStartTime": participant.get("earliestStartTime"),
                "latestEndTime": participant.get("latestEndTime"),
                "sessions": sessions,
            }

        rows = await _gather_flat(participants, _build_row)
        return _merge_attendance_rows(rows, conference_record, params)

    nested_rows = await _gather_flat(resolved["conferenceRecords"], _build_attendance)
    return {
        "input": resolved.get("input"),
        "space": resolved.get("space"),
        "conferenceRecords": resolved["conferenceRecords"],
        "attendance": nested_rows,
    }


def build_google_meet_preflight_report(params: dict[str, Any]) -> dict[str, Any]:
    blockers: list[str] = []
    if not params.get("previewAcknowledged"):
        blockers.append(
            "Set preview.enrollmentAcknowledged=true after confirming your Cloud project, "
            "OAuth principal, and meeting participants are enrolled in the Google Workspace "
            "Developer Preview Program."
        )
    space = params["space"]
    return {
        "input": params["input"],
        "resolvedSpaceName": space["name"],
        "meetingCode": space.get("meetingCode"),
        "meetingUri": space.get("meetingUri"),
        "hasActiveConference": bool(space.get("activeConference")),
        "previewAcknowledged": bool(params.get("previewAcknowledged")),
        "tokenSource": params["tokenSource"],
        "blockers": blockers,
    }


async def _gather(coros: list[Any]) -> list[Any]:
    import asyncio

    return await asyncio.gather(*coros)


async def _gather_flat(items: list[Any], fn: Any) -> list[Any]:
    import asyncio

    if not items:
        return []
    results = await asyncio.gather(*(fn(item) for item in items))
    flat: list[Any] = []
    for result in results:
        if isinstance(result, list):
            flat.extend(result)
        else:
            flat.append(result)
    return flat
