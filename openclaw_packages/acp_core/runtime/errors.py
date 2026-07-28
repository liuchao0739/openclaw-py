from __future__ import annotations

from typing import Any

from ..error_format import redact_sensitive_text, stringify_non_error_cause

ACP_ERROR_CODES = [
    "ACP_BACKEND_MISSING",
    "ACP_BACKEND_UNAVAILABLE",
    "ACP_BACKEND_UNSUPPORTED_CONTROL",
    "ACP_DISPATCH_DISABLED",
    "ACP_INVALID_RUNTIME_OPTION",
    "ACP_SESSION_INIT_FAILED",
    "ACP_TURN_FAILED",
]

AcpRuntimeErrorCode = str
_ACP_ERROR_CODE_SET: set[str] = set(ACP_ERROR_CODES)


class AcpRuntimeError(Exception):
    def __init__(
        self,
        code: AcpRuntimeErrorCode,
        message: str,
        cause: Any = None,
        detail_code: str | None = None,
    ):
        super().__init__(message)
        self.name = "AcpRuntimeError"
        self.code = code
        self.detailCode = detail_code
        self.cause = cause


def _get_foreign_acp_runtime_error(value: Any) -> tuple[str, str] | None:
    if not isinstance(value, Exception):
        return None
    code = getattr(value, "code", None)
    if not isinstance(code, str) or code not in _ACP_ERROR_CODE_SET:
        return None
    return (code, str(value))


def _read_acp_request_error_details(value: Exception) -> str | None:
    code = getattr(value, "code", None)
    if not isinstance(code, int):
        return None
    data = getattr(value, "data", None)
    if data is None or not isinstance(data, dict):
        return None
    details = data.get("details")
    if details is None:
        return None
    rendered = redact_sensitive_text(stringify_non_error_cause(details)).strip()
    return rendered or None


def _message_with_acp_request_error_details(error: Exception) -> str:
    details = _read_acp_request_error_details(error)
    if not details or details in str(error):
        return str(error)
    return f"{str(error)}: {details}"


def is_acp_runtime_error(value: Any) -> bool:
    if isinstance(value, AcpRuntimeError):
        return True
    return _get_foreign_acp_runtime_error(value) is not None


def to_acp_runtime_error(
    error: Any,
    fallback_code: AcpRuntimeErrorCode,
    fallback_message: str,
) -> AcpRuntimeError:
    if isinstance(error, AcpRuntimeError):
        return error
    foreign = _get_foreign_acp_runtime_error(error)
    if foreign is not None:
        return AcpRuntimeError(foreign[0], foreign[1], cause=error)
    if isinstance(error, Exception):
        return AcpRuntimeError(
            fallback_code,
            _message_with_acp_request_error_details(error),
            cause=error,
        )
    return AcpRuntimeError(fallback_code, fallback_message, cause=error)


def _render_single_error(error: Exception) -> str:
    code_value = getattr(error, "code", None)
    code_suffix = f" [{code_value}]" if isinstance(code_value, (str, int)) else ""
    return f"{error.__class__.__name__}{code_suffix}: {str(error)}"


def format_acp_error_chain(error: Any) -> str:
    if not isinstance(error, Exception):
        return redact_sensitive_text(str(error))
    segments: list[str] = [_render_single_error(error)]
    current = getattr(error, "cause", None)
    depth = 0
    while current is not None and depth < 8:
        if isinstance(current, Exception):
            segments.append(_render_single_error(current))
            current = getattr(current, "cause", None)
        else:
            segments.append(stringify_non_error_cause(current))
            current = None
        depth += 1
    return redact_sensitive_text(" <- ".join(segments))


async def with_acp_runtime_error_boundary(
    run: Any,
    fallback_code: AcpRuntimeErrorCode,
    fallback_message: str,
) -> Any:
    try:
        return await run()
    except Exception as error:
        raise to_acp_runtime_error(error, fallback_code, fallback_message)