from typing import Optional, List, Any

from .frames import RequestFrame, ResponseFrame, EventFrame, ErrorFrame, SnapshotFrame, AckFrame
from .frames import Frame, FrameType
from .snapshot import Snapshot, StateVersion, SnapshotKind, SnapshotScope, SnapshotStatus
from .error_codes import ErrorCode
from .primitives import InputProvenance

from .agent import (
    AgentIdentityParams, AgentIdentityResult, AgentParams, AgentEvent, AgentWaitParams,
)
from .agents_models_skills import (
    AgentSummary, AgentsCreateParams, AgentsCreateResult,
    AgentsModelsSkillsGetParams, AgentsModelsSkillsGetResult,
)
from .channels import (
    TalkGetParams, TalkGetResult, TalkEnterParams, TalkEnterResult,
    TalkLeaveParams, TalkLeaveResult, TalkMessageParams, TalkMessageResult, TalkTypingParams,
)
from .commands import CommandsListParams, CommandsListResult
from .config import (
    ConfigGetParams, ConfigGetResult, ConfigUpdateParams, ConfigUpdateResult,
    ConfigPatchParams, ConfigPatchResult,
)
from .cron import (
    CronCreateParams, CronCreateResult, CronUpdateParams, CronUpdateResult,
    CronDeleteParams, CronDeleteResult, CronGetParams, CronGetResult, CronListParams, CronListResult,
)
from .devices import (
    DevicesPairParams, DevicesPairResult, DevicesTrustParams, DevicesTrustResult,
    DevicesListParams, DevicesListResult, DevicesRevokeParams, DevicesRevokeResult,
)
from .environments import (
    EnvironmentsGetParams, EnvironmentsGetResult, EnvironmentsUpdateParams, EnvironmentsUpdateResult,
    EnvironmentsPatchParams, EnvironmentsPatchResult, EnvironmentsDeleteParams, EnvironmentsDeleteResult,
    EnvironmentsCreateParams, EnvironmentsCreateResult, EnvironmentsListParams, EnvironmentsListResult,
)
from .exec_approvals import (
    ExecApprovalsListParams, ExecApprovalsListResult,
    ExecApprovalsReviewParams, ExecApprovalsReviewResult,
)
from .logs_chat import (
    LogsChatGetParams, LogsChatGetResult, LogsChatAppendParams, LogsChatAppendResult,
    LogsChatRotateParams, LogsChatRotateResult,
)
from .nodes import (
    NodesGetParams, NodesGetResult, NodesListParams, NodesListResult,
    NodesAttachParams, NodesAttachResult, NodesDetachParams, NodesDetachResult,
)
from .plugin_approvals import (
    PluginApprovalsListParams, PluginApprovalsListResult,
    PluginApprovalsReviewParams, PluginApprovalsReviewResult,
)
from .plugins import (
    PluginsListParams, PluginsListResult, PluginsInstallParams, PluginsInstallResult,
    PluginsUninstallParams, PluginsUninstallResult, PluginsUpdateParams, PluginsUpdateResult,
    PluginsEnableParams, PluginsEnableResult, PluginsDisableParams, PluginsDisableResult,
    PluginsConfigGetParams, PluginsConfigGetResult, PluginsConfigPatchParams, PluginsConfigPatchResult,
)
from .push import PushParams, PushResult
from .secrets import (
    SecretsListParams, SecretsListResult, SecretsGetParams, SecretsGetResult,
    SecretsCreateParams, SecretsCreateResult, SecretsUpdateParams, SecretsUpdateResult,
    SecretsDeleteParams, SecretsDeleteResult,
)
from .sessions import (
    SessionsCreateParams, SessionsCreateResult, SessionsListParams, SessionsListResult,
    SessionsGetParams, SessionsGetResult, SessionsArchiveParams, SessionsArchiveResult,
    SessionsRestoreParams, SessionsRestoreResult, SessionsCloseParams, SessionsCloseResult,
)
from .tasks import (
    TasksCreateParams, TasksCreateResult, TasksGetParams, TasksGetResult, TasksListParams, TasksListResult,
    TasksStateUpdateParams, TasksStateUpdateResult, TasksTransitionParams, TasksTransitionResult,
    TasksClaimParams, TasksClaimResult, TasksAssignParams, TasksAssignResult,
    TasksUnassignParams, TasksUnassignResult, TasksUpstreamAuthGetParams, TasksUpstreamAuthGetResult,
    TasksUpstreamAuthRefreshParams, TasksUpstreamAuthRefreshResult,
)
from .wizard import (
    WizardCreateParams, WizardCreateResult, WizardGetParams, WizardGetResult,
    WizardUpdateParams, WizardUpdateResult, WizardSubmitParams, WizardSubmitResult,
    WizardDeleteParams, WizardDeleteResult,
)
from .artifacts import (
    ArtifactsListParams, ArtifactsListResult, ArtifactsGetParams, ArtifactsGetResult,
    ArtifactsPushParams, ArtifactsPushResult, ArtifactsPullParams, ArtifactsPullResult,
    ArtifactsDeleteParams, ArtifactsDeleteResult,
)

class ChatSendParams:
    session_key: str
    message: str
    provenance: Optional[InputProvenance]
    metadata: Optional[dict]

class ChatSendResult:
    session_key: str
    run_id: str
    status: str
    metadata: Optional[dict]

class ChatSessionKeysGetParams:
    agent_id: Optional[str]
    metadata: Optional[dict]

class ChatSessionKeysGetResult:
    session_keys: List[str]
    metadata: Optional[dict]

class FramesErrorParams:
    error_code: ErrorCode
    error_message: Optional[str]
    metadata: Optional[dict]

class FramesErrorResult:
    error_code: ErrorCode
    error_message: Optional[str]
    metadata: Optional[dict]

class FramesSnapshotParams:
    snapshot: Snapshot
    metadata: Optional[dict]

class FramesSnapshotResult:
    snapshot: Optional[Snapshot]
    metadata: Optional[dict]

class FramesAckParams:
    ack_id: str
    metadata: Optional[dict]

class FramesAckResult:
    ack_id: str
    metadata: Optional[dict]