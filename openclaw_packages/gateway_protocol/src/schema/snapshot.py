from typing import Literal, Final, Optional, List, Any

StateVersion = Literal[1, 2, 3, 4]

STATE_VERSION_UNSET: Final[StateVersion] = 1
STATE_VERSION_LEGACY: Final[StateVersion] = 2
STATE_VERSION_CANONICAL: Final[StateVersion] = 3
STATE_VERSION_FUTURE: Final[StateVersion] = 4
CURRENT_STATE_VERSION: Final[StateVersion] = 3
MINIMUM_STATE_VERSION: Final[StateVersion] = 1
MAXIMUM_STATE_VERSION: Final[StateVersion] = 4

STATE_VERSIONS: Final[tuple] = (
    STATE_VERSION_UNSET,
    STATE_VERSION_LEGACY,
    STATE_VERSION_CANONICAL,
    STATE_VERSION_FUTURE,
)

SnapshotScope = Literal["agent", "control-ui", "debugger", "node", "runner", "session", "task"]

SNAPSHOT_SCOPE_AGENT: Final[SnapshotScope] = "agent"
SNAPSHOT_SCOPE_CONTROL_UI: Final[SnapshotScope] = "control-ui"
SNAPSHOT_SCOPE_DEBUGGER: Final[SnapshotScope] = "debugger"
SNAPSHOT_SCOPE_NODE: Final[SnapshotScope] = "node"
SNAPSHOT_SCOPE_RUNNER: Final[SnapshotScope] = "runner"
SNAPSHOT_SCOPE_SESSION: Final[SnapshotScope] = "session"
SNAPSHOT_SCOPE_TASK: Final[SnapshotScope] = "task"

SNAPSHOT_SCOPES: Final[tuple] = (
    SNAPSHOT_SCOPE_AGENT,
    SNAPSHOT_SCOPE_CONTROL_UI,
    SNAPSHOT_SCOPE_DEBUGGER,
    SNAPSHOT_SCOPE_NODE,
    SNAPSHOT_SCOPE_RUNNER,
    SNAPSHOT_SCOPE_SESSION,
    SNAPSHOT_SCOPE_TASK,
)

SnapshotKind = Literal[
    "agent-identity",
    "agent-state",
    "config",
    "gateway",
    "node",
    "profile",
    "run",
    "session",
    "task",
]

SNAPSHOT_KIND_AGENT_IDENTITY: Final[SnapshotKind] = "agent-identity"
SNAPSHOT_KIND_AGENT_STATE: Final[SnapshotKind] = "agent-state"
SNAPSHOT_KIND_CONFIG: Final[SnapshotKind] = "config"
SNAPSHOT_KIND_GATEWAY: Final[SnapshotKind] = "gateway"
SNAPSHOT_KIND_NODE: Final[SnapshotKind] = "node"
SNAPSHOT_KIND_PROFILE: Final[SnapshotKind] = "profile"
SNAPSHOT_KIND_RUN: Final[SnapshotKind] = "run"
SNAPSHOT_KIND_SESSION: Final[SnapshotKind] = "session"
SNAPSHOT_KIND_TASK: Final[SnapshotKind] = "task"

SNAPSHOT_KINDS: Final[tuple] = (
    SNAPSHOT_KIND_AGENT_IDENTITY,
    SNAPSHOT_KIND_AGENT_STATE,
    SNAPSHOT_KIND_CONFIG,
    SNAPSHOT_KIND_GATEWAY,
    SNAPSHOT_KIND_NODE,
    SNAPSHOT_KIND_PROFILE,
    SNAPSHOT_KIND_RUN,
    SNAPSHOT_KIND_SESSION,
    SNAPSHOT_KIND_TASK,
)

SnapshotStatus = Literal["active", "archived", "deleted", "inactive"]

SNAPSHOT_STATUS_ACTIVE: Final[SnapshotStatus] = "active"
SNAPSHOT_STATUS_ARCHIVED: Final[SnapshotStatus] = "archived"
SNAPSHOT_STATUS_DELETED: Final[SnapshotStatus] = "deleted"
SNAPSHOT_STATUS_INACTIVE: Final[SnapshotStatus] = "inactive"

SNAPSHOT_STATUSES: Final[tuple] = (
    SNAPSHOT_STATUS_ACTIVE,
    SNAPSHOT_STATUS_ARCHIVED,
    SNAPSHOT_STATUS_DELETED,
    SNAPSHOT_STATUS_INACTIVE,
)

class Snapshot:
    def __init__(
        self,
        kind: SnapshotKind,
        scope: SnapshotScope,
        content: Any,
        *,
        version: StateVersion = CURRENT_STATE_VERSION,
        status: SnapshotStatus = SNAPSHOT_STATUS_ACTIVE,
        id: Optional[str] = None,
        created_at: Optional[str] = None,
        updated_at: Optional[str] = None,
        expires_at: Optional[str] = None,
        ttl_s: Optional[int] = None,
        metadata: Optional[dict] = None,
        tags: Optional[List[str]] = None,
        labels: Optional[List[str]] = None,
        error: Optional[str] = None,
        warnings: Optional[List[str]] = None,
    ):
        self.id = id
        self.version = version
        self.kind = kind
        self.scope = scope
        self.status = status
        self.created_at = created_at
        self.updated_at = updated_at
        self.expires_at = expires_at
        self.ttl_s = ttl_s
        self.content = content
        self.metadata = metadata
        self.tags = tags or []
        self.labels = labels or []
        self.error = error
        self.warnings = warnings or []
