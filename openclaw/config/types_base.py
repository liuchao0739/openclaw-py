from __future__ import annotations

from typing import Any, Literal

ReplyMode = Literal["text", "command"]
TypingMode = Literal["never", "instant", "thinking", "message"]
SessionScope = Literal["per-sender", "global"]
DmScope = Literal["main", "per-peer", "per-channel-peer", "per-account-channel-peer"]
ReplyToMode = Literal["off", "first", "all", "batched"]
GroupPolicy = Literal["open", "disabled", "allowlist"]
DmPolicy = Literal["pairing", "allowlist", "open", "disabled"]
ContextVisibilityMode = Literal["all", "allowlist", "allowlist_quote"]
TextChunkMode = Literal["length", "newline"]
StreamingMode = Literal["off", "partial", "block", "progress"]
ChannelStreamingCommandTextMode = Literal["raw", "status"]
MarkdownTableMode = Literal["off", "bullets", "code", "block"]
SessionSendPolicyAction = Literal["allow", "deny"]
SessionResetMode = Literal["daily", "idle"]
SessionMaintenanceMode = Literal["enforce", "warn"]


class OutboundRetryConfig(dict):
    pass


class BlockStreamingCoalesceConfig(dict):
    pass


class BlockStreamingChunkConfig(dict):
    pass


class ChannelStreamingProgressConfig(dict):
    pass


class ChannelStreamingPreviewConfig(dict):
    pass


class ChannelStreamingBlockConfig(dict):
    pass


class ChannelStreamingConfig(dict):
    pass


class ChannelDeliveryStreamingConfig(dict):
    pass


class ChannelPreviewStreamingConfig(dict):
    pass


class MarkdownConfig(dict):
    pass


class HumanDelayConfig(dict):
    pass


class SessionSendPolicyMatch(dict):
    pass


class SessionSendPolicyRule(dict):
    pass


class SessionSendPolicyConfig(dict):
    pass


class SessionResetConfig(dict):
    pass


class SessionResetByTypeConfig(dict):
    pass


class SessionThreadBindingsConfig(dict):
    pass


class SessionWriteLockConfig(dict):
    pass


class SessionMaintenanceConfig(dict):
    pass


class SessionConfig(dict):
    pass


class LoggingConfig(dict):
    pass


class DiagnosticsOtelConfig(dict):
    pass


class DiagnosticsCacheTraceConfig(dict):
    pass


class DiagnosticsConfig(dict):
    pass


class WebReconnectConfig(dict):
    pass


class WebWhatsAppConfig(dict):
    pass


class WebConfig(dict):
    pass


class IdentityConfig(dict):
    pass


class AgentElevatedAllowFromConfig(dict):
    pass


class SurfaceConfigEntry(dict):
    pass


class ConfigValidationIssue(dict):
    pass


class LegacyConfigIssue(dict):
    pass


class ConfigFileSnapshot(dict):
    pass


class SourceConfig(dict):
    pass


class ResolvedSourceConfig(dict):
    pass


class RuntimeConfig(dict):
    pass
