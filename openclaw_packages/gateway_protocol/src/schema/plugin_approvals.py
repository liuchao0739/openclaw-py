from typing import Literal, Final, Optional, List, Any

MODEL_APPROVAL_DECISION = Literal["approve", "reject", "revoke"]

MODEL_APPROVAL_DECISION_APPROVE: Literal["approve"] = "approve"
MODEL_APPROVAL_DECISION_REJECT: Literal["reject"] = "reject"
MODEL_APPROVAL_DECISION_REVOKE: Literal["revoke"] = "revoke"

MODEL_APPROVAL_DECISIONS: Final[tuple] = (
    MODEL_APPROVAL_DECISION_APPROVE,
    MODEL_APPROVAL_DECISION_REJECT,
    MODEL_APPROVAL_DECISION_REVOKE,
)

class PluginApproval:
    approval_id: str
    plugin_id: str
    decision: Optional[MODEL_APPROVAL_DECISION]
    metadata: Optional[dict]

class PluginApprovalsListParams:
    status: Optional[str]
    metadata: Optional[dict]

class PluginApprovalsListResult:
    approvals: List[PluginApproval]
    metadata: Optional[dict]

class PluginApprovalsReviewParams:
    approval_id: str
    decision: MODEL_APPROVAL_DECISION
    comment: Optional[str]
    metadata: Optional[dict]

class PluginApprovalsReviewResult:
    approval_id: str
    decision: MODEL_APPROVAL_DECISION
    metadata: Optional[dict]
