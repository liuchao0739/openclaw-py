from typing import Literal, Final, Optional, List, Any

from .primitives import InputProvenance
from .snapshot import Snapshot, StateVersion
from .error_codes import ErrorCode

FrameType = Literal[
    "agent.identity.get",
    "agent.identity.result",
    "agent.identity.update",
    "agent.params.get",
    "agent.params.result",
    "agent.params.update",
    "agent.wait.get",
    "agent.wait.result",
    "agent.wait.update",
    "agent.event",
    "agent.summary.get",
    "agent.summary.result",
    "agents.create",
    "agents.create.result",
    "agents.models.skills.get",
    "agents.models.skills.result",
    "chat.send",
    "chat.send.result",
    "chat.session.keys.get",
    "chat.session.keys.result",
    "channels.talk.get",
    "channels.talk.result",
    "channels.talk.enter",
    "channels.talk.leave",
    "channels.talk.message",
    "channels.talk.typing",
    "channels.talk.enter.result",
    "channels.talk.leave.result",
    "commands.list",
    "commands.list.result",
    "config.get",
    "config.result",
    "config.update",
    "config.patch",
    "cron.create",
    "cron.create.result",
    "cron.update",
    "cron.update.result",
    "cron.delete",
    "cron.delete.result",
    "cron.get",
    "cron.result",
    "cron.list",
    "cron.list.result",
    "devices.pair",
    "devices.pair.result",
    "devices.trust",
    "devices.trust.result",
    "devices.list",
    "devices.list.result",
    "devices.revoke",
    "devices.revoke.result",
    "environments.get",
    "environments.result",
    "environments.update",
    "environments.patch",
    "environments.delete",
    "environments.create",
    "environments.list",
    "environments.list.result",
    "exec.approvals.list",
    "exec.approvals.list.result",
    "exec.approvals.review",
    "exec.approvals.review.result",
    "logs.chat.get",
    "logs.chat.result",
    "logs.chat.append",
    "logs.chat.rotate",
    "nodes.get",
    "nodes.result",
    "nodes.list",
    "nodes.list.result",
    "nodes.attach",
    "nodes.attach.result",
    "nodes.detach",
    "nodes.detach.result",
    "plugin.approvals.list",
    "plugin.approvals.list.result",
    "plugin.approvals.review",
    "plugin.approvals.review.result",
    "plugins.list",
    "plugins.list.result",
    "plugins.install",
    "plugins.install.result",
    "plugins.uninstall",
    "plugins.uninstall.result",
    "plugins.update",
    "plugins.update.result",
    "plugins.enable",
    "plugins.disable",
    "plugins.config.get",
    "plugins.config.result",
    "plugins.config.patch",
    "push",
    "push.result",
    "secrets.list",
    "secrets.list.result",
    "secrets.get",
    "secrets.result",
    "secrets.create",
    "secrets.create.result",
    "secrets.update",
    "secrets.update.result",
    "secrets.delete",
    "secrets.delete.result",
    "sessions.create",
    "sessions.create.result",
    "sessions.list",
    "sessions.list.result",
    "sessions.get",
    "sessions.result",
    "sessions.archive",
    "sessions.archive.result",
    "sessions.restore",
    "sessions.restore.result",
    "sessions.close",
    "sessions.close.result",
    "tasks.create",
    "tasks.create.result",
    "tasks.get",
    "tasks.result",
    "tasks.list",
    "tasks.list.result",
    "tasks.state.update",
    "tasks.state.update.result",
    "tasks.transition",
    "tasks.transition.result",
    "tasks.claim",
    "tasks.claim.result",
    "tasks.assign",
    "tasks.assign.result",
    "tasks.unassign",
    "tasks.unassign.result",
    "tasks.upstream.auth.get",
    "tasks.upstream.auth.result",
    "tasks.upstream.auth.refresh",
    "tasks.upstream.auth.refresh.result",
    "wizard.create",
    "wizard.create.result",
    "wizard.get",
    "wizard.result",
    "wizard.update",
    "wizard.update.result",
    "wizard.submit",
    "wizard.submit.result",
    "wizard.delete",
    "wizard.delete.result",
    "artifacts.list",
    "artifacts.list.result",
    "artifacts.get",
    "artifacts.result",
    "artifacts.push",
    "artifacts.push.result",
    "artifacts.pull",
    "artifacts.pull.result",
    "artifacts.delete",
    "artifacts.delete.result",
    "frames.error",
    "frames.snapshot",
    "frames.snapshot.result",
    "frames.ack",
]

FRAME_TYPE_REQUEST: Literal["request"] = "request"
FRAME_TYPE_RESPONSE: Literal["response"] = "response"
FRAME_TYPE_EVENT: Literal["event"] = "event"
FRAME_TYPE_ERROR: Literal["error"] = "error"
FRAME_TYPE_SNAPSHOT: Literal["snapshot"] = "snapshot"
FRAME_TYPE_ACK: Literal["ack"] = "ack"

FrameTypeCategory = Literal["request", "response", "event", "error", "snapshot", "ack"]

class RequestFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        method: str,
        params: Optional[Any] = None,
        provenance: Optional[InputProvenance] = None,
        ttl_ms: Optional[int] = None,
        deadline_ms: Optional[int] = None,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.method = method
        self.params = params
        self.provenance = provenance
        self.ttl_ms = ttl_ms
        self.deadline_ms = deadline_ms
        self.state_version = state_version
        self.metadata = metadata

class ResponseFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        method: str,
        result: Optional[Any] = None,
        error_code: Optional[ErrorCode] = None,
        error_message: Optional[str] = None,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.method = method
        self.result = result
        self.error_code = error_code
        self.error_message = error_message
        self.state_version = state_version
        self.metadata = metadata

class EventFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        method: str,
        payload: Optional[Any] = None,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.method = method
        self.payload = payload
        self.state_version = state_version
        self.metadata = metadata

class ErrorFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        method: Optional[str] = None,
        error_code: ErrorCode,
        error_message: Optional[str] = None,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.method = method
        self.error_code = error_code
        self.error_message = error_message
        self.state_version = state_version
        self.metadata = metadata

class SnapshotFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        snapshot: Snapshot,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.snapshot = snapshot
        self.state_version = state_version
        self.metadata = metadata

class AckFrame:
    def __init__(
        self,
        *,
        id: str,
        type: FrameType,
        ack_id: str,
        state_version: Optional[StateVersion] = None,
        metadata: Optional[dict] = None,
    ):
        self.id = id
        self.type = type
        self.ack_id = ack_id
        self.state_version = state_version
        self.metadata = metadata

Frame = Any
