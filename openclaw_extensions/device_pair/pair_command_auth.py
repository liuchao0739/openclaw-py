from typing import Dict, List, Optional


COMMAND_OWNER_PAIRING_SCOPES = ["operator.pairing"]
PAIRING_SCOPE = "operator.pairing"
ADMIN_SCOPE = "operator.admin"
TALK_SECRETS_SCOPE = "operator.talk.secrets"


def normalize_lowercase_string_or_empty(value: Optional[str]) -> str:
    return value.strip().lower() if value else ""


def isInternalGatewayPairingCaller(params: Dict) -> bool:
    return params.get("channel") == "webchat" or isinstance(params.get("gatewayClientScopes"), list)


def hasPairingPrivilege(scopes: List[str]) -> bool:
    return PAIRING_SCOPE in scopes or ADMIN_SCOPE in scopes


def hasSetupHandoffPrivilege(scopes: List[str]) -> bool:
    return TALK_SECRETS_SCOPE in scopes or ADMIN_SCOPE in scopes


def resolvePairingCommandAuthState(params: Dict) -> Dict:
    is_internal_gateway_caller = isInternalGatewayPairingCaller(params)
    if is_internal_gateway_caller:
        approval_caller_scopes = params.get("gatewayClientScopes") or []
        return {
            "isInternalGatewayCaller": is_internal_gateway_caller,
            "isMissingPairingPrivilege": not hasPairingPrivilege(approval_caller_scopes),
            "isMissingSetupHandoffPrivilege": not hasSetupHandoffPrivilege(approval_caller_scopes),
            "approvalCallerScopes": approval_caller_scopes,
        }

    if params.get("senderIsOwner") is True:
        return {
            "isInternalGatewayCaller": is_internal_gateway_caller,
            "isMissingPairingPrivilege": False,
            "isMissingSetupHandoffPrivilege": False,
            "approvalCallerScopes": COMMAND_OWNER_PAIRING_SCOPES,
        }

    return {
        "isInternalGatewayCaller": is_internal_gateway_caller,
        "isMissingPairingPrivilege": True,
        "isMissingSetupHandoffPrivilege": True,
        "approvalCallerScopes": None,
    }


def buildMissingPairingScopeReply() -> Dict:
    return {"text": "⚠️ This command requires operator.pairing."}


def buildMissingSetupHandoffScopeReply() -> Dict:
    return {"text": "⚠️ Setup code handoff includes Talk secrets and requires operator.talk.secrets."}

__all__ = [
    "resolvePairingCommandAuthState",
    "buildMissingPairingScopeReply",
    "buildMissingSetupHandoffScopeReply",
]