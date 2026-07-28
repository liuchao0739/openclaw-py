from __future__ import annotations

import re
from typing import Any, Optional

_NORMALIZE_OPTIONAL_STRING_RE = re.compile(r"\s+")


def _normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _is_record(value: Any) -> bool:
    return bool(value) and isinstance(value, dict)


def _is_non_empty_string(value: Any) -> bool:
    return isinstance(value, str) and len(value) > 0


def _is_non_negative_integer(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


CONNECT_ERROR_DETAIL_CODES = {
    "AUTH_REQUIRED",
    "AUTH_UNAUTHORIZED",
    "AUTH_TOKEN_MISSING",
    "AUTH_TOKEN_MISMATCH",
    "AUTH_TOKEN_NOT_CONFIGURED",
    "AUTH_PASSWORD_MISSING",
    "AUTH_PASSWORD_MISMATCH",
    "AUTH_PASSWORD_NOT_CONFIGURED",
    "AUTH_BOOTSTRAP_TOKEN_INVALID",
    "AUTH_DEVICE_TOKEN_MISMATCH",
    "AUTH_SCOPE_MISMATCH",
    "AUTH_RATE_LIMITED",
    "AUTH_TAILSCALE_IDENTITY_MISSING",
    "AUTH_TAILSCALE_PROXY_MISSING",
    "AUTH_TAILSCALE_WHOIS_FAILED",
    "AUTH_TAILSCALE_IDENTITY_MISMATCH",
    "CONTROL_UI_ORIGIN_NOT_ALLOWED",
    "PROTOCOL_MISMATCH",
    "CONTROL_UI_DEVICE_IDENTITY_REQUIRED",
    "DEVICE_IDENTITY_REQUIRED",
    "DEVICE_AUTH_INVALID",
    "DEVICE_AUTH_DEVICE_ID_MISMATCH",
    "DEVICE_AUTH_SIGNATURE_EXPIRED",
    "DEVICE_AUTH_NONCE_REQUIRED",
    "DEVICE_AUTH_NONCE_MISMATCH",
    "DEVICE_AUTH_SIGNATURE_INVALID",
    "DEVICE_AUTH_PUBLIC_KEY_INVALID",
    "PAIRING_REQUIRED",
    "CLIENT_VERSION_MISMATCH",
}

CONNECT_PAIRING_REQUIRED_REASONS = {
    "not-paired",
    "role-upgrade",
    "scope-upgrade",
    "metadata-upgrade",
}

CONNECT_RECOVERY_NEXT_STEP_VALUES = {
    "retry_with_device_token",
    "update_auth_configuration",
    "update_auth_credentials",
    "wait_then_retry",
    "review_auth_configuration",
}

CONNECT_PAIRING_REQUIRED_MESSAGE_BY_REASON = {
    "not-paired": "device pairing required",
    "role-upgrade": "role upgrade pending approval",
    "scope-upgrade": "scope upgrade pending approval",
    "metadata-upgrade": "device metadata change pending approval",
}

PAIRING_CONNECT_REQUEST_ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._:-]{0,127}$")


def read_connect_error_detail_code(details: Any) -> Optional[str]:
    if not details or not isinstance(details, dict):
        return None
    code = details.get("code")
    if isinstance(code, str) and code.strip():
        return code
    return None


def read_connect_error_recovery_advice(details: Any) -> dict:
    if not details or not isinstance(details, dict):
        return {}
    raw = details
    can_retry_with_device_token = (
        raw.get("canRetryWithDeviceToken")
        if isinstance(raw.get("canRetryWithDeviceToken"), bool)
        else None
    )
    normalized_next_step = _normalize_optional_string(raw.get("recommendedNextStep")) or ""
    recommended_next_step = (
        normalized_next_step
        if normalized_next_step in CONNECT_RECOVERY_NEXT_STEP_VALUES
        else None
    )
    result = {}
    if can_retry_with_device_token is not None:
        result["canRetryWithDeviceToken"] = can_retry_with_device_token
    if recommended_next_step is not None:
        result["recommendedNextStep"] = recommended_next_step
    return result


def _normalize_pairing_connect_reason(value: Any) -> Optional[str]:
    normalized = _normalize_optional_string(value) or ""
    if normalized in CONNECT_PAIRING_REQUIRED_REASONS:
        return normalized
    return None


def _normalize_pairing_connect_request_id(value: Any) -> Optional[str]:
    normalized = _normalize_optional_string(value)
    if normalized and PAIRING_CONNECT_REQUEST_ID_PATTERN.match(normalized):
        return normalized
    return None


def _normalize_string_array(value: Any) -> Optional[list[str]]:
    if not isinstance(value, list):
        return None
    result = []
    for entry in value:
        normalized = _normalize_optional_string(entry)
        if normalized:
            result.append(normalized)
    return result if result else None


def _create_pairing_connect_error_details(**params: Any) -> dict:
    result = {"code": "PAIRING_REQUIRED"}
    for key in (
        "reason", "requestId", "remediationHint", "recommendedNextStep",
        "retryable", "pauseReconnect", "deviceId", "requestedRole",
        "requestedScopes", "approvedRoles", "approvedScopes",
    ):
        val = params.get(key)
        if val is not None:
            result[key] = val
    return result


def read_pairing_connect_error_details(details: Any) -> Optional[dict]:
    if read_connect_error_detail_code(details) != "PAIRING_REQUIRED":
        return None
    if not details or not isinstance(details, dict):
        return None

    reason = _normalize_pairing_connect_reason(details.get("reason"))
    request_id = _normalize_pairing_connect_request_id(details.get("requestId"))
    remediation_hint = (
        _normalize_optional_string(details.get("remediationHint"))
        or "Approve the pending device request before retrying."
    )
    normalized_next_step = _normalize_optional_string(details.get("recommendedNextStep")) or ""
    recommended_next_step = (
        normalized_next_step
        if normalized_next_step in CONNECT_RECOVERY_NEXT_STEP_VALUES
        else None
    )
    device_id = _normalize_optional_string(details.get("deviceId"))
    requested_role = _normalize_optional_string(details.get("requestedRole"))
    requested_scopes = _normalize_string_array(details.get("requestedScopes"))
    approved_roles = _normalize_string_array(details.get("approvedRoles"))
    approved_scopes = _normalize_string_array(details.get("approvedScopes"))

    retryable = details.get("retryable") if isinstance(details.get("retryable"), bool) else None
    pause_reconnect = details.get("pauseReconnect") if isinstance(details.get("pauseReconnect"), bool) else None

    return _create_pairing_connect_error_details(
        reason=reason,
        requestId=request_id,
        remediationHint=remediation_hint,
        recommendedNextStep=recommended_next_step,
        retryable=retryable,
        pauseReconnect=pause_reconnect,
        deviceId=device_id,
        requestedRole=requested_role,
        requestedScopes=requested_scopes,
        approvedRoles=approved_roles,
        approvedScopes=approved_scopes,
    )


def _format_protocol_mismatch_message(message: Optional[str], details: Any) -> str:
    if not isinstance(details, dict):
        details = {}

    def _normalize_protocol_number(value: Any) -> Optional[int]:
        if isinstance(value, int) and not isinstance(value, bool) and value > 0:
            return value
        return None

    client_min = _normalize_protocol_number(details.get("clientMinProtocol"))
    client_max = _normalize_protocol_number(details.get("clientMaxProtocol"))
    expected = _normalize_protocol_number(details.get("expectedProtocol"))
    probe_min = _normalize_protocol_number(details.get("minimumProbeProtocol"))
    parts = []
    if client_min is not None and client_max is not None:
        parts.append(
            f"Control UI v{client_min}"
            if client_min == client_max
            else f"Control UI v{client_min}-v{client_max}"
        )
    if expected is not None:
        parts.append(f"Gateway v{expected}")
    if probe_min is not None:
        parts.append(f"probe min v{probe_min}")
    normalized = _normalize_optional_string(message) or "protocol mismatch"
    return f"{normalized}: {', '.join(parts)}" if parts else normalized


def format_connect_error_message(params: dict) -> str:
    message = params.get("message")
    details = params.get("details")

    if read_connect_error_detail_code(details) == "PAIRING_REQUIRED":
        pairing = read_pairing_connect_error_details(details)
        base = CONNECT_PAIRING_REQUIRED_MESSAGE_BY_REASON.get(
            pairing["reason"] if pairing else "not-paired",
            "device pairing required",
        )
        if pairing and pairing.get("requestId"):
            return f"{base} (requestId: {pairing['requestId']})"
        return base

    if read_connect_error_detail_code(details) == "PROTOCOL_MISMATCH":
        return _format_protocol_mismatch_message(message, details)

    return _normalize_optional_string(message) or "gateway request failed"


GATEWAY_STARTUP_UNAVAILABLE_REASON = "startup-sidecars"
GATEWAY_STARTUP_RETRY_AFTER_MS = 500
GATEWAY_STARTUP_RETRY_MIN_MS = 100
GATEWAY_STARTUP_RETRY_MAX_MS = 2_000


def _is_gateway_startup_unavailable_details(details: Any) -> bool:
    return (
        isinstance(details, dict)
        and details.get("reason") == GATEWAY_STARTUP_UNAVAILABLE_REASON
    )


def _is_retryable_gateway_startup_unavailable_error(error: Any) -> bool:
    if not isinstance(error, dict):
        return False
    code = error.get("gatewayCode") or error.get("code")
    return (
        code == "UNAVAILABLE"
        and error.get("retryable") is True
        and _is_gateway_startup_unavailable_details(error.get("details"))
    )


def resolve_gateway_startup_retry_after_ms(error: Any) -> Optional[int]:
    if not _is_retryable_gateway_startup_unavailable_error(error):
        return None
    retry_after_ms = error.get("retryAfterMs")
    if isinstance(retry_after_ms, (int, float)) and retry_after_ms == retry_after_ms:
        raw = int(retry_after_ms)
    else:
        raw = GATEWAY_STARTUP_RETRY_AFTER_MS
    return min(max(raw, GATEWAY_STARTUP_RETRY_MIN_MS), GATEWAY_STARTUP_RETRY_MAX_MS)
