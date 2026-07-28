from __future__ import annotations

import re
from enum import Enum
from typing import Any

CIAO_CANCELLATION_MESSAGE_RE = re.compile(
    r"^CIAO (?:ANNOUNCEMENT|PROBING) CANCELLED\b", re.UNICODE
)
CIAO_INTERFACE_ASSERTION_MESSAGE_RE = re.compile(
    r"REACHED ILLEGAL STATE!?\s+IPV4 ADDRESS CHANGED? FROM (?:DEFINED TO UNDEFINED|UNDEFINED TO DEFINED)!?",
    re.UNICODE,
)
CIAO_NETMASK_ASSERTION_MESSAGE_RE = re.compile(
    r"IP ADDRESS VERSION MUST MATCH\.\s+NETMASK CANNOT HAVE A VERSION DIFFERENT FROM THE ADDRESS!?",
    re.UNICODE,
)
CIAO_SELF_PROBE_MESSAGE_RE = re.compile(
    r"CAN'T PROBE FOR A SERVICE WHICH IS ANNOUNCED ALREADY\.\s+RECEIVED (?:PROBING|ANNOUNCING|ANNOUNCED) FOR SERVICE\b",
    re.UNICODE,
)
CIAO_INTERFACE_ENUMERATION_FAILURE_RE = re.compile(
    r"\bUV_INTERFACE_ADDRESSES\b", re.UNICODE
)


class CiaoProcessErrorKind(str, Enum):
    CANCELLATION = "cancellation"
    INTERFACE_ASSERTION = "interface-assertion"
    NETMASK_ASSERTION = "netmask-assertion"
    SELF_PROBE = "self-probe"
    INTERFACE_ENUMERATION_FAILURE = "interface-enumeration-failure"


def _format_bonjour_error(value: Any) -> str:
    if isinstance(value, Exception):
        return str(value)
    return str(value)


def _collect_error_graph_candidates(reason: Any) -> list[Any]:
    candidates: list[Any] = []
    seen: set[int] = set()

    def _visit(current: Any) -> None:
        if current is None:
            return
        current_id = id(current)
        if current_id in seen:
            return
        seen.add(current_id)
        candidates.append(current)
        if isinstance(current, Exception):
            for attr in ("__cause__", "__context__"):
                cause = getattr(current, attr, None)
                if cause is not None:
                    _visit(cause)
        if isinstance(current, dict):
            for key in ("cause", "reason", "original", "error", "data"):
                val = current.get(key)
                if val is not None:
                    _visit(val)
            errors = current.get("errors")
            if isinstance(errors, list):
                for err in errors:
                    _visit(err)
        elif hasattr(current, "cause"):
            _visit(getattr(current, "cause", None))
        elif hasattr(current, "reason"):
            _visit(getattr(current, "reason", None))
        elif hasattr(current, "original"):
            _visit(getattr(current, "original", None))
        elif hasattr(current, "error"):
            _visit(getattr(current, "error", None))
        elif hasattr(current, "data"):
            _visit(getattr(current, "data", None))

    _visit(reason)
    return candidates


def classify_ciao_process_error(
    reason: Any,
) -> tuple[str, str] | None:
    for candidate in _collect_error_graph_candidates(reason):
        formatted = _format_bonjour_error(candidate)
        message = formatted.upper()
        if CIAO_CANCELLATION_MESSAGE_RE.match(message):
            return (CiaoProcessErrorKind.CANCELLATION.value, formatted)
        if CIAO_INTERFACE_ASSERTION_MESSAGE_RE.match(message):
            return (CiaoProcessErrorKind.INTERFACE_ASSERTION.value, formatted)
        if CIAO_NETMASK_ASSERTION_MESSAGE_RE.match(message):
            return (CiaoProcessErrorKind.NETMASK_ASSERTION.value, formatted)
        if CIAO_SELF_PROBE_MESSAGE_RE.match(message):
            return (CiaoProcessErrorKind.SELF_PROBE.value, formatted)
        if CIAO_INTERFACE_ENUMERATION_FAILURE_RE.match(message):
            return (
                CiaoProcessErrorKind.INTERFACE_ENUMERATION_FAILURE.value,
                formatted,
            )
    return None