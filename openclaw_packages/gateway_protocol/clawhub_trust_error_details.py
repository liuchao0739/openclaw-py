from typing import Literal, Final, Optional, List

class ClawHubTrustErrorCodes:
    SECURITY_UNAVAILABLE: Literal["clawhub_security_unavailable"] = "clawhub_security_unavailable"
    RISK_ACKNOWLEDGEMENT_REQUIRED: Literal["clawhub_risk_acknowledgement_required"] = "clawhub_risk_acknowledgement_required"
    DOWNLOAD_BLOCKED: Literal["clawhub_download_blocked"] = "clawhub_download_blocked"

ClawHubTrustErrorCode = Literal[
    "clawhub_security_unavailable",
    "clawhub_risk_acknowledgement_required",
    "clawhub_download_blocked",
]

CLAWHUB_TRUST_ERROR_CODES: Final[tuple] = (
    ClawHubTrustErrorCodes.SECURITY_UNAVAILABLE,
    ClawHubTrustErrorCodes.RISK_ACKNOWLEDGEMENT_REQUIRED,
    ClawHubTrustErrorCodes.DOWNLOAD_BLOCKED,
)

class ClawHubTrustErrorDetails:
    def __init__(
        self,
        *,
        code: ClawHubTrustErrorCode,
        message: Optional[str] = None,
        acknowledgement_token: Optional[str] = None,
        blocked_url: Optional[str] = None,
        details: Optional[dict] = None,
    ):
        self.code = code
        self.message = message
        self.acknowledgement_token = acknowledgement_token
        self.blocked_url = blocked_url
        self.details = details

def build_clawhub_trust_error_details(
    code: ClawHubTrustErrorCode,
    message: Optional[str] = None,
    acknowledgement_token: Optional[str] = None,
    blocked_url: Optional[str] = None,
    details: Optional[dict] = None,
) -> ClawHubTrustErrorDetails:
    return ClawHubTrustErrorDetails(
        code=code,
        message=message,
        acknowledgement_token=acknowledgement_token,
        blocked_url=blocked_url,
        details=details,
    )

def is_clawhub_trust_error_code(code: str) -> bool:
    return code in CLAWHUB_TRUST_ERROR_CODES

def read_clawhub_trust_error_details(data: dict) -> Optional[ClawHubTrustErrorDetails]:
    if not data:
        return None
    return ClawHubTrustErrorDetails(
        code=data.get("code", ""),
        message=data.get("message"),
        acknowledgement_token=data.get("acknowledgement_token"),
        blocked_url=data.get("blocked_url"),
        details=data.get("details"),
    )
