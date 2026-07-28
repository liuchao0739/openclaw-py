from __future__ import annotations

from typing import Any


class TerminalOutcome:
    SUCCESS = "success"
    ERROR = "error"
    ABORTED = "aborted"
    TIMEOUT = "timeout"
    COMPACTION = "compaction"


def describe_terminal_outcome(outcome: str) -> str:
    return outcome.replace("_", " ").title()
