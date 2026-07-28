from typing import Literal, Final, Optional, List, Any

WIZARD_STATUS = Literal["active", "cancelled", "completed", "failed"]

WIZARD_STATUS_ACTIVE: Literal["active"] = "active"
WIZARD_STATUS_CANCELLED: Literal["cancelled"] = "cancelled"
WIZARD_STATUS_COMPLETED: Literal["completed"] = "completed"
WIZARD_STATUS_FAILED: Literal["failed"] = "failed"

WIZARD_STATUSES: Final[tuple] = (
    WIZARD_STATUS_ACTIVE,
    WIZARD_STATUS_CANCELLED,
    WIZARD_STATUS_COMPLETED,
    WIZARD_STATUS_FAILED,
)

class Wizard:
    wizard_id: str
    title: str
    description: Optional[str]
    status: WIZARD_STATUS
    metadata: Optional[dict]

class WizardCreateParams:
    title: str
    description: Optional[str]
    metadata: Optional[dict]

class WizardCreateResult:
    wizard_id: str
    metadata: Optional[dict]

class WizardGetParams:
    wizard_id: str
    metadata: Optional[dict]

class WizardGetResult:
    wizard: Optional[Wizard]
    metadata: Optional[dict]

class WizardUpdateParams:
    wizard_id: str
    patch: Any
    metadata: Optional[dict]

class WizardUpdateResult:
    wizard_id: str
    metadata: Optional[dict]

class WizardSubmitParams:
    wizard_id: str
    metadata: Optional[dict]

class WizardSubmitResult:
    wizard_id: str
    status: WIZARD_STATUS
    metadata: Optional[dict]

class WizardDeleteParams:
    wizard_id: str
    metadata: Optional[dict]

class WizardDeleteResult:
    wizard_id: str
    metadata: Optional[dict]
