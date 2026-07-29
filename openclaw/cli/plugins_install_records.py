from __future__ import annotations

from typing import Any

INSTALL_RECORDS: dict[str, dict] = {}


def add_install_record(name: str, record: dict) -> None:
    INSTALL_RECORDS[name] = record


def get_install_record(name: str) -> dict | None:
    return INSTALL_RECORDS.get(name)


def list_install_records() -> list[str]:
    return list(INSTALL_RECORDS.keys())


def remove_install_record(name: str) -> None:
    INSTALL_RECORDS.pop(name, None)
