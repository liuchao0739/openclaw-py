import time
from typing import Any, Dict, List, Optional, TypedDict, Union


class DiagnosticErrorInfo(TypedDict, total=False):
    name: Optional[str]
    message: str
    stack: Optional[str]
    code: Optional[Union[str, int]]


class AssistantMessageDiagnostic(TypedDict, total=False):
    type: str
    timestamp: int
    error: Optional[DiagnosticErrorInfo]
    details: Optional[Dict[str, Any]]


def format_thrown_value(value: Any) -> str:
    if isinstance(value, BaseException):
        return str(value) or type(value).__name__
    if isinstance(value, str):
        return value
    return str(value)


def extract_diagnostic_error(error: Any) -> DiagnosticErrorInfo:
    if not isinstance(error, BaseException):
        return {"name": "ThrownValue", "message": format_thrown_value(error)}
    code = getattr(error, "code", None)
    return {
        "name": type(error).__name__ or None,
        "message": str(error) or type(error).__name__,
        "stack": "".join(__import__("traceback").format_exception(type(error), error, error.__traceback__)) or None,
        "code": code if isinstance(code, (str, int)) and not isinstance(code, bool) else None,
    }


def create_assistant_message_diagnostic(
    type: str,
    error: Any,
    details: Optional[Dict[str, Any]] = None,
) -> AssistantMessageDiagnostic:
    return {
        "type": type,
        "timestamp": int(time.time() * 1000),
        "error": extract_diagnostic_error(error),
        "details": details,
    }


def append_assistant_message_diagnostic(
    message: dict,
    diagnostic: AssistantMessageDiagnostic,
) -> None:
    existing = message.get("diagnostics") or []
    existing = list(existing)
    existing.append(diagnostic)
    message["diagnostics"] = existing
