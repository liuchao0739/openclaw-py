"""Repairs legacy cron job identity fields into the canonical id shape.

Mirrors src/cron/normalize-job-identity.ts.
"""

from __future__ import annotations

from typing import Any, Mapping, MutableMapping


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def normalize_cron_job_identity_fields(
    raw: MutableMapping[str, Any],
) -> dict[str, bool]:
    """Normalize mutable cron job rows from old ``jobId`` storage into ``id``.

    Mutates ``raw`` in place: sets ``id`` from ``jobId`` when ``id`` is empty,
    and removes the legacy ``jobId`` key if present.

    Returns ``{"mutated": bool, "legacy_job_id_issue": bool}``.
    """
    raw_id = _normalize_optional_string(raw.get("id")) or ""
    legacy_job_id = _normalize_optional_string(raw.get("jobId")) or ""
    had_job_id_key = "jobId" in raw
    normalized_id = raw_id or legacy_job_id
    id_changed = bool(normalized_id and raw.get("id") != normalized_id)

    if id_changed:
        raw["id"] = normalized_id
    if had_job_id_key:
        del raw["jobId"]
    return {"mutated": id_changed or had_job_id_key, "legacy_job_id_issue": had_job_id_key}
