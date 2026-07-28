from typing import Literal, Final, Optional, List, Any

TASK_STATE = Literal[
    "blocked",
    "cancelled",
    "completed",
    "deferred",
    "failed",
    "in_progress",
    "not_started",
    "ready",
    "waiting",
]

TASK_STATE_BLOCKED: Literal["blocked"] = "blocked"
TASK_STATE_CANCELLED: Literal["cancelled"] = "cancelled"
TASK_STATE_COMPLETED: Literal["completed"] = "completed"
TASK_STATE_DEFERRED: Literal["deferred"] = "deferred"
TASK_STATE_FAILED: Literal["failed"] = "failed"
TASK_STATE_IN_PROGRESS: Literal["in_progress"] = "in_progress"
TASK_STATE_NOT_STARTED: Literal["not_started"] = "not_started"
TASK_STATE_READY: Literal["ready"] = "ready"
TASK_STATE_WAITING: Literal["waiting"] = "waiting"

TASK_STATES: Final[tuple] = (
    TASK_STATE_BLOCKED,
    TASK_STATE_CANCELLED,
    TASK_STATE_COMPLETED,
    TASK_STATE_DEFERRED,
    TASK_STATE_FAILED,
    TASK_STATE_IN_PROGRESS,
    TASK_STATE_NOT_STARTED,
    TASK_STATE_READY,
    TASK_STATE_WAITING,
)

TASK_TRANSITION = Literal[
    "block",
    "cancel",
    "complete",
    "defer",
    "fail",
    "start",
    "start_ready",
    "submit",
    "unblock",
]

TASK_TRANSITION_BLOCK: Literal["block"] = "block"
TASK_TRANSITION_CANCEL: Literal["cancel"] = "cancel"
TASK_TRANSITION_COMPLETE: Literal["complete"] = "complete"
TASK_TRANSITION_DEFER: Literal["defer"] = "defer"
TASK_TRANSITION_FAIL: Literal["fail"] = "fail"
TASK_TRANSITION_START: Literal["start"] = "start"
TASK_TRANSITION_START_READY: Literal["start_ready"] = "start_ready"
TASK_TRANSITION_SUBMIT: Literal["submit"] = "submit"
TASK_TRANSITION_UNBLOCK: Literal["unblock"] = "unblock"

TASK_TRANSITIONS: Final[tuple] = (
    TASK_TRANSITION_BLOCK,
    TASK_TRANSITION_CANCEL,
    TASK_TRANSITION_COMPLETE,
    TASK_TRANSITION_DEFER,
    TASK_TRANSITION_FAIL,
    TASK_TRANSITION_START,
    TASK_TRANSITION_START_READY,
    TASK_TRANSITION_SUBMIT,
    TASK_TRANSITION_UNBLOCK,
)

TASK_ASSIGNMENT_KIND = Literal["claim", "manual", "upstream"]

TASK_ASSIGNMENT_KIND_CLAIM: Literal["claim"] = "claim"
TASK_ASSIGNMENT_KIND_MANUAL: Literal["manual"] = "manual"
TASK_ASSIGNMENT_KIND_UPSTREAM: Literal["upstream"] = "upstream"

TASK_ASSIGNMENT_KINDS: Final[tuple] = (
    TASK_ASSIGNMENT_KIND_CLAIM,
    TASK_ASSIGNMENT_KIND_MANUAL,
    TASK_ASSIGNMENT_KIND_UPSTREAM,
)

TASK_KIND = Literal["delegation", "normal", "upstream"]

TASK_KIND_DELEGATION: Literal["delegation"] = "delegation"
TASK_KIND_NORMAL: Literal["normal"] = "normal"
TASK_KIND_UPSTREAM: Literal["upstream"] = "upstream"

TASK_KINDS: Final[tuple] = (
    TASK_KIND_DELEGATION,
    TASK_KIND_NORMAL,
    TASK_KIND_UPSTREAM,
)

TASK_SECURITY_STATE = Literal["blocked", "clear", "warn"]

TASK_SECURITY_STATE_BLOCKED: Literal["blocked"] = "blocked"
TASK_SECURITY_STATE_CLEAR: Literal["clear"] = "clear"
TASK_SECURITY_STATE_WARN: Literal["warn"] = "warn"

TASK_SECURITY_STATES: Final[tuple] = (
    TASK_SECURITY_STATE_BLOCKED,
    TASK_SECURITY_STATE_CLEAR,
    TASK_SECURITY_STATE_WARN,
)

UPSTREAM_AUTH_SCHEME = Literal["bearer", "oauth2-client-credentials", "oauth2-refresh", "oauth2-device", "api-key", "basic", "aws-iam", "unknown"]

UPSTREAM_AUTH_SCHEME_BEARER: Literal["bearer"] = "bearer"
UPSTREAM_AUTH_SCHEME_OAUTH2_CLIENT_CREDENTIALS: Literal["oauth2-client-credentials"] = "oauth2-client-credentials"
UPSTREAM_AUTH_SCHEME_OAUTH2_REFRESH: Literal["oauth2-refresh"] = "oauth2-refresh"
UPSTREAM_AUTH_SCHEME_OAUTH2_DEVICE: Literal["oauth2-device"] = "oauth2-device"
UPSTREAM_AUTH_SCHEME_API_KEY: Literal["api-key"] = "api-key"
UPSTREAM_AUTH_SCHEME_BASIC: Literal["basic"] = "basic"
UPSTREAM_AUTH_SCHEME_AWS_IAM: Literal["aws-iam"] = "aws-iam"
UPSTREAM_AUTH_SCHEME_UNKNOWN: Literal["unknown"] = "unknown"

UPSTREAM_AUTH_SCHEMES: Final[tuple] = (
    UPSTREAM_AUTH_SCHEME_BEARER,
    UPSTREAM_AUTH_SCHEME_OAUTH2_CLIENT_CREDENTIALS,
    UPSTREAM_AUTH_SCHEME_OAUTH2_REFRESH,
    UPSTREAM_AUTH_SCHEME_OAUTH2_DEVICE,
    UPSTREAM_AUTH_SCHEME_API_KEY,
    UPSTREAM_AUTH_SCHEME_BASIC,
    UPSTREAM_AUTH_SCHEME_AWS_IAM,
    UPSTREAM_AUTH_SCHEME_UNKNOWN,
)

class Task:
    task_id: str
    title: str
    description: Optional[str]
    parent_id: Optional[str]
    assignee: Optional[str]
    kind: TASK_KIND
    state: TASK_STATE
    security_state: TASK_SECURITY_STATE
    metadata: Optional[dict]

class TasksCreateParams:
    task_id: Optional[str]
    title: str
    description: Optional[str]
    parent_id: Optional[str]
    assignee: Optional[str]
    kind: Optional[TASK_KIND]
    metadata: Optional[dict]

class TasksCreateResult:
    task_id: str
    metadata: Optional[dict]

class TasksGetParams:
    task_id: str
    metadata: Optional[dict]

class TasksGetResult:
    task: Optional[Task]
    metadata: Optional[dict]

class TasksListParams:
    metadata: Optional[dict]

class TasksListResult:
    tasks: List[Task]
    metadata: Optional[dict]

class TasksStateUpdateParams:
    task_id: str
    state: TASK_STATE
    metadata: Optional[dict]

class TasksStateUpdateResult:
    task_id: str
    state: TASK_STATE
    metadata: Optional[dict]

class TasksTransitionParams:
    task_id: str
    transition: TASK_TRANSITION
    metadata: Optional[dict]

class TasksTransitionResult:
    task_id: str
    state: TASK_STATE
    metadata: Optional[dict]

class TasksClaimParams:
    task_id: str
    metadata: Optional[dict]

class TasksClaimResult:
    task_id: str
    assignee: Optional[str]
    metadata: Optional[dict]

class TasksAssignParams:
    task_id: str
    assignee: str
    metadata: Optional[dict]

class TasksAssignResult:
    task_id: str
    assignee: str
    metadata: Optional[dict]

class TasksUnassignParams:
    task_id: str
    metadata: Optional[dict]

class TasksUnassignResult:
    task_id: str
    metadata: Optional[dict]

class TasksUpstreamAuthGetParams:
    task_id: str
    metadata: Optional[dict]

class TasksUpstreamAuthGetResult:
    task_id: str
    scheme: UPSTREAM_AUTH_SCHEME
    credentials: Optional[dict]
    metadata: Optional[dict]

class TasksUpstreamAuthRefreshParams:
    task_id: str
    metadata: Optional[dict]

class TasksUpstreamAuthRefreshResult:
    task_id: str
    metadata: Optional[dict]
