from typing import Literal, Final, Optional, List

ConnectErrorDetailCode = Literal[
    "AUTH_REQUIRED",
    "AUTH_UNAUTHORIZED",
    "CLIENT_ID_REQUIRED",
    "CLIENT_ID_UNKNOWN",
    "CLIENT_VERSION_OUT_OF_DATE",
    "PROTOCOL_VERSION_OUT_OF_DATE",
    "PROTOCOL_VERSION_TOO_NEW",
    "PROTOCOL_VERSION_TOO_OLD",
    "GATEWAY_NOT_FOUND",
    "GATEWAY_VERSION_MISMATCH",
    "NODE_NOT_FOUND",
    "NODE_DISABLED",
    "UPSTREAM_AUTH_FAILED",
    "UPSTREAM_AUTH_REQUIRED",
    "UPSTREAM_NOT_AVAILABLE",
    "UPSTREAM_UNREACHABLE",
    "DOWNSTREAM_AUTH_FAILED",
    "DOWNSTREAM_AUTH_REQUIRED",
    "DOWNSTREAM_NOT_AVAILABLE",
    "DOWNSTREAM_UNREACHABLE",
    "DOWNSTREAM_PROTOCOL_NEGOTIATION_FAILED",
    "DOWNSTREAM_PROTOCOL_VERSION_UNSUPPORTED",
    "DOWNSTREAM_QUOTA_EXCEEDED",
    "DOWNSTREAM_RATE_LIMITED",
    "SECURITY_UNAVAILABLE",
    "SECURITY_BLOCKED",
    "CERT_EXPIRED",
    "CERT_UNTRUSTED",
    "CERT_VALIDATION_FAILED",
    "CA_CERT_EXPIRED",
    "CA_CERT_UNTRUSTED",
    "CA_CERT_VALIDATION_FAILED",
    "CA_CERT_MISSING",
    "CA_CERT_REQUIRED",
    "CA_CERT_VALIDATION_UNAVAILABLE",
    "RESTART_REQUIRED",
    "MAINTENANCE",
    "RESOURCE_EXHAUSTED",
    "NOT_ENOUGH_CAPACITY",
    "INTERNAL_SERVER_ERROR",
    "SERVICE_UNAVAILABLE",
    "UPGRADE_REQUIRED",
    "STUN_NOT_AVAILABLE",
    "STUN_QUERY_FAILED",
    "STUN_QUERY_TIMEOUT",
    "STUN_REQUIRED",
    "STUN_SERVER_NOT_FOUND",
    "STUN_SERVER_UNREACHABLE",
    "STUN_UNAVAILABLE",
    "STUN_UPGRADE_FAILED",
    "STUN_UPGRADE_REQUIRED",
    "STUN_VERSION_MISMATCH",
    "STUN_VERSION_NOT_SUPPORTED",
    "STUN_VERSION_TOO_OLD",
    "STUN_VIOLATION",
    "LICENSE_EXCEEDED",
    "LICENSE_EXPIRED",
    "LICENSE_NOT_FOUND",
    "LICENSE_NOT_SUPPORTED",
    "VALIDATION_FAILED",
]

ConnectRecoveryNextStep = Literal[
    "retry",
    "upgrade_client",
    "contact_admin",
    "check_credentials",
    "check_configuration",
    "check_network",
    "check_firewall",
    "check_certificates",
    "check_ca_certificates",
    "check_upstream",
    "check_downstream",
    "check_security",
    "check_license",
    "check_stun",
    "restart_gateway",
    "wait_and_retry",
]

class ConnectErrorDetails:
    def __init__(
        self,
        *,
        code: ConnectErrorDetailCode,
        message: Optional[str] = None,
        recovery: Optional[ConnectRecoveryNextStep] = None,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.recovery = recovery
        self.details = details

def build_connect_error_details(
    code: ConnectErrorDetailCode,
    message: Optional[str] = None,
    recovery: Optional[ConnectRecoveryNextStep] = None,
    details: Optional[dict] = None,
) -> ConnectErrorDetails:
    return ConnectErrorDetails(code=code, message=message, recovery=recovery, details=details)

def read_connect_error_details(data: dict) -> Optional[ConnectErrorDetails]:
    if not data:
        return None
    return ConnectErrorDetails(
        code=data.get("code", ""),
        message=data.get("message"),
        recovery=data.get("recovery"),
        details=data.get("details"),
    )
