from typing import Dict, List, Optional

from .api import approveDevicePairing, listDevicePairing
from .notify import formatPendingRequests
from .api import normalize_lowercase_string_or_empty, normalize_optional_string


def buildMultiplePendingApprovalReply(pending: List[Dict]) -> Dict:
    return {
        "text": (
            f"{formatPendingRequests(pending)}\n\n"
            "Multiple pending requests found. Approve one explicitly:\n"
            "/pair approve <requestId>\n"
            "Or approve the most recent:\n"
            "/pair approve latest"
        )
    }


def selectPendingApprovalRequest(params: Dict) -> Dict:
    pending = params.get("pending", [])
    requested = params.get("requested")

    if len(pending) == 0:
        return {"reply": {"text": "No pending device pairing requests."}}

    if not requested:
        if len(pending) == 1:
            return {"pending": pending[0]}
        else:
            return {"reply": buildMultiplePendingApprovalReply(pending)}

    if normalize_lowercase_string_or_empty(requested) == "latest":
        latest = pending[0]
        for entry in pending[1:]:
            if (entry.get("ts") or 0) > (latest.get("ts") or 0):
                latest = entry
        return {"pending": latest}

    return {
        "pending": next((entry for entry in pending if entry.get("requestId") == requested), None),
    }


def formatApprovedPairingReply(approved: Dict) -> Dict:
    device = approved.get("device", {})
    label = normalize_optional_string(device.get("displayName")) or device.get("deviceId", "unknown")
    platform = normalize_optional_string(device.get("platform"))
    platform_label = f" ({platform})" if platform else ""
    return {"text": f"✅ Paired {label}{platform_label}."}


def formatForbiddenPairingRequirement(approved: Dict) -> str:
    return approved.get("scope") or approved.get("role") or "additional approval"


async def approvePendingPairingRequest(params: Dict) -> Dict:
    request_id = params.get("requestId")
    caller_scopes = params.get("callerScopes")

    if caller_scopes is None:
        approved = await approveDevicePairing(request_id)
    else:
        approved = await approveDevicePairing(request_id, {"callerScopes": caller_scopes})

    if not approved:
        return {"text": "Pairing request not found."}

    if approved.get("status") == "forbidden":
        return {
            "text": f"⚠️ This command requires {formatForbiddenPairingRequirement(approved)} to approve this pairing request."
        }

    return formatApprovedPairingReply(approved)

__all__ = ["selectPendingApprovalRequest", "approvePendingPairingRequest"]