from typing import Literal, Final, Optional, List, Any

PUSH_POLICY = Literal["manual", "auto"]

PUSH_POLICY_MANUAL: Literal["manual"] = "manual"
PUSH_POLICY_AUTO: Literal["auto"] = "auto"

PUSH_POLICIES: Final[tuple] = (
    PUSH_POLICY_MANUAL,
    PUSH_POLICY_AUTO,
)

PUSH_STATUS = Literal["pending", "pushed", "failed", "skipped"]

PUSH_STATUS_PENDING: Literal["pending"] = "pending"
PUSH_STATUS_PUSHED: Literal["pushed"] = "pushed"
PUSH_STATUS_FAILED: Literal["failed"] = "failed"
PUSH_STATUS_SKIPPED: Literal["skipped"] = "skipped"

PUSH_STATUSES: Final[tuple] = (
    PUSH_STATUS_PENDING,
    PUSH_STATUS_PUSHED,
    PUSH_STATUS_FAILED,
    PUSH_STATUS_SKIPPED,
)

class PushParams:
    push_policy: PUSH_POLICY
    metadata: Optional[dict]

class PushResult:
    push_status: PUSH_STATUS
    metadata: Optional[dict]
