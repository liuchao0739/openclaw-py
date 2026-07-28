from typing import Optional, List, Any, Literal

from .frames import FrameType

PROTOCOL_VERSION = 4
MIN_CLIENT_PROTOCOL_VERSION = 4
MIN_PROBE_PROTOCOL_VERSION = 4

AGENT_RUN_STATUS = Literal["cancelled", "completed", "failed", "running", "scheduled"]
AGENT_RUN_STATUS_CANCELLED: Literal["cancelled"] = "cancelled"
AGENT_RUN_STATUS_COMPLETED: Literal["completed"] = "completed"
AGENT_RUN_STATUS_FAILED: Literal["failed"] = "failed"
AGENT_RUN_STATUS_RUNNING: Literal["running"] = "running"
AGENT_RUN_STATUS_SCHEDULED: Literal["scheduled"] = "scheduled"

AGENT_IDENTITY_KIND = Literal["cli", "external", "native"]
AGENT_IDENTITY_KIND_CLI: Literal["cli"] = "cli"
AGENT_IDENTITY_KIND_EXTERNAL: Literal["external"] = "external"
AGENT_IDENTITY_KIND_NATIVE: Literal["native"] = "native"

CHAT_SEND_SESSION_KEY_MAX_LENGTH = 256
SESSION_LABEL_MAX_LENGTH = 256

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

TASK_ASSIGNMENT_KIND = Literal["claim", "manual", "upstream"]
TASK_ASSIGNMENT_KIND_CLAIM: Literal["claim"] = "claim"
TASK_ASSIGNMENT_KIND_MANUAL: Literal["manual"] = "manual"
TASK_ASSIGNMENT_KIND_UPSTREAM: Literal["upstream"] = "upstream"

UPSTREAM_AUTH_SCHEME = Literal["bearer", "oauth2-client-credentials", "oauth2-refresh", "oauth2-device", "api-key", "basic", "aws-iam", "unknown"]
UPSTREAM_AUTH_SCHEME_BEARER: Literal["bearer"] = "bearer"
UPSTREAM_AUTH_SCHEME_OAUTH2_CLIENT_CREDENTIALS: Literal["oauth2-client-credentials"] = "oauth2-client-credentials"
UPSTREAM_AUTH_SCHEME_OAUTH2_REFRESH: Literal["oauth2-refresh"] = "oauth2-refresh"
UPSTREAM_AUTH_SCHEME_OAUTH2_DEVICE: Literal["oauth2-device"] = "oauth2-device"
UPSTREAM_AUTH_SCHEME_API_KEY: Literal["api-key"] = "api-key"
UPSTREAM_AUTH_SCHEME_BASIC: Literal["basic"] = "basic"
UPSTREAM_AUTH_SCHEME_AWS_IAM: Literal["aws-iam"] = "aws-iam"
UPSTREAM_AUTH_SCHEME_UNKNOWN: Literal["unknown"] = "unknown"

CHANNEL_KIND = Literal["group", "one-to-one"]
CHANNEL_KIND_GROUP: Literal["group"] = "group"
CHANNEL_KIND_ONE_TO_ONE: Literal["one-to-one"] = "one-to-one"

CHANNEL_ROLE = Literal["admin", "member", "owner", "read-only"]
CHANNEL_ROLE_ADMIN: Literal["admin"] = "admin"
CHANNEL_ROLE_MEMBER: Literal["member"] = "member"
CHANNEL_ROLE_OWNER: Literal["owner"] = "owner"
CHANNEL_ROLE_READ_ONLY: Literal["read-only"] = "read-only"

DEVICES_TRUST_LEVEL = Literal["trusted", "untrusted"]
DEVICES_TRUST_LEVEL_TRUSTED: Literal["trusted"] = "trusted"
DEVICES_TRUST_LEVEL_UNTRUSTED: Literal["untrusted"] = "untrusted"

EXEC_APPROVAL_DECISION = Literal["approve", "reject", "revoke"]
EXEC_APPROVAL_DECISION_APPROVE: Literal["approve"] = "approve"
EXEC_APPROVAL_DECISION_REJECT: Literal["reject"] = "reject"
EXEC_APPROVAL_DECISION_REVOKE: Literal["revoke"] = "revoke"

MODEL_APPROVAL_DECISION = Literal["approve", "reject", "revoke"]
MODEL_APPROVAL_DECISION_APPROVE: Literal["approve"] = "approve"
MODEL_APPROVAL_DECISION_REJECT: Literal["reject"] = "reject"
MODEL_APPROVAL_DECISION_REVOKE: Literal["revoke"] = "revoke"

PLUGIN_APPROVAL_DECISION = Literal["approve", "reject", "revoke"]
PLUGIN_APPROVAL_DECISION_APPROVE: Literal["approve"] = "approve"
PLUGIN_APPROVAL_DECISION_REJECT: Literal["reject"] = "reject"
PLUGIN_APPROVAL_DECISION_REVOKE: Literal["revoke"] = "revoke"

PUSH_POLICY = Literal["manual", "auto"]
PUSH_POLICY_MANUAL: Literal["manual"] = "manual"
PUSH_POLICY_AUTO: Literal["auto"] = "auto"

PUSH_STATUS = Literal["pending", "pushed", "failed", "skipped"]
PUSH_STATUS_PENDING: Literal["pending"] = "pending"
PUSH_STATUS_PUSHED: Literal["pushed"] = "pushed"
PUSH_STATUS_FAILED: Literal["failed"] = "failed"
PUSH_STATUS_SKIPPED: Literal["skipped"] = "skipped"

PLUGIN_TYPE = Literal["extension", "middleware", "tool"]
PLUGIN_TYPE_EXTENSION: Literal["extension"] = "extension"
PLUGIN_TYPE_MIDDLEWARE: Literal["middleware"] = "middleware"
PLUGIN_TYPE_TOOL: Literal["tool"] = "tool"

SECRET_KIND = Literal["env", "file", "value"]
SECRET_KIND_ENV: Literal["env"] = "env"
SECRET_KIND_FILE: Literal["file"] = "file"
SECRET_KIND_VALUE: Literal["value"] = "value"

SESSION_TYPE = Literal["agent", "agentless", "debug", "probe"]
SESSION_TYPE_AGENT: Literal["agent"] = "agent"
SESSION_TYPE_AGENTLESS: Literal["agentless"] = "agentless"
SESSION_TYPE_DEBUG: Literal["debug"] = "debug"
SESSION_TYPE_PROBE: Literal["probe"] = "probe"

WIZARD_STATUS = Literal["active", "cancelled", "completed", "failed"]
WIZARD_STATUS_ACTIVE: Literal["active"] = "active"
WIZARD_STATUS_CANCELLED: Literal["cancelled"] = "cancelled"
WIZARD_STATUS_COMPLETED: Literal["completed"] = "completed"
WIZARD_STATUS_FAILED: Literal["failed"] = "failed"

ARTIFACT_TYPE = Literal["directory", "file"]
ARTIFACT_TYPE_DIRECTORY: Literal["directory"] = "directory"
ARTIFACT_TYPE_FILE: Literal["file"] = "file"

ARTIFACT_PUSH_POLICY = Literal["manual", "auto"]
ARTIFACT_PUSH_POLICY_MANUAL: Literal["manual"] = "manual"
ARTIFACT_PUSH_POLICY_AUTO: Literal["auto"] = "auto"

CRON_SCHEDULE_KIND = Literal["every", "cron", "at"]
CRON_SCHEDULE_KIND_EVERY: Literal["every"] = "every"
CRON_SCHEDULE_KIND_CRON: Literal["cron"] = "cron"
CRON_SCHEDULE_KIND_AT: Literal["at"] = "at"

CRON_JOB_STATUS = Literal["active", "paused", "deleted"]
CRON_JOB_STATUS_ACTIVE: Literal["active"] = "active"
CRON_JOB_STATUS_PAUSED: Literal["paused"] = "paused"
CRON_JOB_STATUS_DELETED: Literal["deleted"] = "deleted"

LOG_LEVEL = Literal["debug", "info", "warn", "error"]
LOG_LEVEL_DEBUG: Literal["debug"] = "debug"
LOG_LEVEL_INFO: Literal["info"] = "info"
LOG_LEVEL_WARN: Literal["warn"] = "warn"
LOG_LEVEL_ERROR: Literal["error"] = "error"

NODE_KIND = Literal["managed", "unmanaged"]
NODE_KIND_MANAGED: Literal["managed"] = "managed"
NODE_KIND_UNMANAGED: Literal["unmanaged"] = "unmanaged"

NODE_STATE = Literal["attached", "detached", "offline", "online", "unreachable"]
NODE_STATE_ATTACHED: Literal["attached"] = "attached"
NODE_STATE_DETACHED: Literal["detached"] = "detached"
NODE_STATE_OFFLINE: Literal["offline"] = "offline"
NODE_STATE_ONLINE: Literal["online"] = "online"
NODE_STATE_UNREACHABLE: Literal["unreachable"] = "unreachable"

SECURITY_STATE = Literal["blocked", "clear", "warn"]
SECURITY_STATE_BLOCKED: Literal["blocked"] = "blocked"
SECURITY_STATE_CLEAR: Literal["clear"] = "clear"
SECURITY_STATE_WARN: Literal["warn"] = "warn"

TASK_KIND = Literal["delegation", "normal", "upstream"]
TASK_KIND_DELEGATION: Literal["delegation"] = "delegation"
TASK_KIND_NORMAL: Literal["normal"] = "normal"
TASK_KIND_UPSTREAM: Literal["upstream"] = "upstream"

TASK_SECURITY_STATE = Literal["blocked", "clear", "warn"]
TASK_SECURITY_STATE_BLOCKED: Literal["blocked"] = "blocked"
TASK_SECURITY_STATE_CLEAR: Literal["clear"] = "clear"
TASK_SECURITY_STATE_WARN: Literal["warn"] = "warn"
