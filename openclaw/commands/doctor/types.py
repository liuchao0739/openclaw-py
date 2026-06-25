"""Shared doctor JSON shapes used by repair modules."""

from __future__ import annotations

from typing import Any

DoctorAccountRecord = dict[str, Any]
DoctorAllowFromEntry = str | int
DoctorAllowFromList = list[DoctorAllowFromEntry]
