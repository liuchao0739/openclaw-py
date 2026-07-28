from typing import Literal, Final, Optional, List, Any

EXEC_APPROVAL_DECISION = Literal["approve", "reject", "revoke"]

EXEC_APPROVAL_DECISION_APPROVE: Literal["approve"] = "approve"
EXEC_APPROVAL_DECISION_REJECT: Literal["reject"] = "reject"
EXEC_APPROVAL_DECISION_REVOKE: Literal["revoke"] = "revoke"

EXEC_APPROVAL_DECISIONS: Final[tuple] = (
    EXEC_APPROVAL_DECISION_APPROVE,
    EXEC_APPROVAL_DECISION_REJECT,
    EXEC_APPROVAL_DECISION_REVOKE,
)

class ExecApproval:
    approval_id: str
    tool_name: str
    args: Optional[dict]
    decision: Optional[EXEC_APPROVAL_DECISION]
    metadata: Optional[dict]

class ExecApprovalsListParams:
    status: Optional[str]
    metadata: Optional[dict]

class ExecApprovalsListResult:
    approvals: List[ExecApproval]
    metadata: Optional[dict]

class ExecApprovalsReviewParams:
    approval_id: str
    decision: EXEC_APPROVAL_DECISION
    comment: Optional[str]
    metadata: Optional[dict]

class ExecApprovalsReviewResult:
    approval_id: str
    decision: EXEC_APPROVAL_DECISION
    metadata: Optional[dict]
