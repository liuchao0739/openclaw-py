from __future__ import annotations

from typing import Any


DoctorAccountRecord = dict[str, Any]
DoctorAllowFromEntry = str | int
DoctorAllowFromList = list[DoctorAllowFromEntry]


class DoctorOptions:
    def __init__(self) -> None:
        self.fix: str | None = None
        self.scan: bool = False
        self.yes: bool = False
        self.json: bool = False
