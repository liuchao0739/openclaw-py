from __future__ import annotations

from typing import Any

from openclaw.commands.doctor.types import DoctorAccountRecord, DoctorAllowFromEntry, DoctorAllowFromList


def _validate_allow_from_entry(entry: Any) -> bool:
    if isinstance(entry, str):
        return True
    if isinstance(entry, int):
        return 0 <= entry <= 255
    return False


def normalize_allow_from_list(raw: DoctorAllowFromList | None = None) -> DoctorAllowFromList:
    if raw is None:
        return []
    return [e for e in raw if _validate_allow_from_entry(e)]


def validate_account_record(record: DoctorAccountRecord) -> list[str]:
    errors: list[str] = []
    if not isinstance(record, dict):
        return ["Account record must be an object."]
    if "accountId" not in record:
        errors.append("Missing accountId field.")
    return errors
