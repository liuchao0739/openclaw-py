"""Shared types for embedded agent runner (minimal port)."""

from __future__ import annotations

from typing import Literal, TypedDict

EmbeddedRunLivenessState = Literal["working", "blocked", "paused", "abandoned"]

FailureSignalCode = Literal["SYSTEM_RUN_DENIED", "INVALID_REQUEST"]


class EmbeddedRunFailureSignal(TypedDict, total=False):
    kind: Literal["execution_denied"]
    source: Literal["tool"]
    toolName: str
    code: FailureSignalCode
    message: str
    fatalForCron: bool