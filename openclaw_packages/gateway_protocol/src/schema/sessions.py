from typing import Literal, Final, Optional, List, Any

SESSION_TYPE = Literal["agent", "agentless", "debug", "probe"]

SESSION_TYPE_AGENT: Literal["agent"] = "agent"
SESSION_TYPE_AGENTLESS: Literal["agentless"] = "agentless"
SESSION_TYPE_DEBUG: Literal["debug"] = "debug"
SESSION_TYPE_PROBE: Literal["probe"] = "probe"

SESSION_TYPES: Final[tuple] = (
    SESSION_TYPE_AGENT,
    SESSION_TYPE_AGENTLESS,
    SESSION_TYPE_DEBUG,
    SESSION_TYPE_PROBE,
)

SESSION_LABEL_MAX_LENGTH = 256

class Session:
    session_id: str
    session_type: SESSION_TYPE
    agent_id: Optional[str]
    status: Optional[str]
    label: Optional[str]
    metadata: Optional[dict]

class SessionsCreateParams:
    session_type: SESSION_TYPE
    agent_id: Optional[str]
    metadata: Optional[dict]

class SessionsCreateResult:
    session_id: str
    session_type: SESSION_TYPE
    metadata: Optional[dict]

class SessionsListParams:
    metadata: Optional[dict]

class SessionsListResult:
    sessions: List[Session]
    metadata: Optional[dict]

class SessionsGetParams:
    session_id: Optional[str]
    metadata: Optional[dict]

class SessionsGetResult:
    session: Optional[Session]
    metadata: Optional[dict]

class SessionsArchiveParams:
    session_id: str
    metadata: Optional[dict]

class SessionsArchiveResult:
    session_id: str
    metadata: Optional[dict]

class SessionsRestoreParams:
    session_id: str
    metadata: Optional[dict]

class SessionsRestoreResult:
    session_id: str
    metadata: Optional[dict]

class SessionsCloseParams:
    session_id: str
    metadata: Optional[dict]

class SessionsCloseResult:
    session_id: str
    metadata: Optional[dict]
