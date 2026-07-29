from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ChannelDefaultsConfig(BaseModel):
    group_policy: str | None = Field(default=None, alias="groupPolicy")
    context_visibility: str | None = Field(default=None, alias="contextVisibility")
    heartbeat: dict[str, Any] | None = None
    bot_loop_protection: dict[str, Any] | None = Field(default=None, alias="botLoopProtection")

    model_config = {"populate_by_name": True}


class ExtensionNestedPolicyConfig(BaseModel):
    policy: str | None = None
    allow_from: list[str | int] | None = Field(default=None, alias="allowFrom")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExtensionAccountConfig(ExtensionNestedPolicyConfig):
    default_to: str | int | None = Field(default=None, alias="defaultTo")
    dm_policy: str | None = Field(default=None, alias="dmPolicy")
    dm: ExtensionNestedPolicyConfig | None = None
    media_max_mb: int | None = Field(default=None, alias="mediaMaxMb")
    config_writes: bool | None = Field(default=None, alias="configWrites")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExtensionChannelConfig(BaseModel):
    enabled: bool | None = None
    allow_from: list[str | int] | None = Field(default=None, alias="allowFrom")
    default_to: str | int | None = Field(default=None, alias="defaultTo")
    default_account: str | None = Field(default=None, alias="defaultAccount")
    dm_policy: str | None = Field(default=None, alias="dmPolicy")
    group_policy: str | None = Field(default=None, alias="groupPolicy")
    context_visibility: str | None = Field(default=None, alias="contextVisibility")
    health_monitor: dict[str, Any] | None = Field(default=None, alias="healthMonitor")
    dm: ExtensionNestedPolicyConfig | None = None
    network: dict[str, Any] | None = None
    groups: dict[str, Any] | None = None
    rooms: dict[str, Any] | None = None
    media_max_mb: int | None = Field(default=None, alias="mediaMaxMb")
    callback_base_url: str | None = Field(default=None, alias="callbackBaseUrl")
    interactions: dict[str, Any] | None = None
    exec_approvals: dict[str, Any] | None = Field(default=None, alias="execApprovals")
    thread_bindings: dict[str, Any] | None = Field(default=None, alias="threadBindings")
    bot_loop_protection: dict[str, Any] | None = Field(default=None, alias="botLoopProtection")
    dangerously_allow_private_network: bool | None = Field(
        default=None, alias="dangerouslyAllowPrivateNetwork"
    )
    accounts: dict[str, ExtensionAccountConfig] | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ChannelsConfig(BaseModel):
    defaults: ChannelDefaultsConfig | None = None
    model_by_channel: dict[str, dict[str, str]] | None = Field(
        default=None, alias="modelByChannel"
    )
    discord: ExtensionChannelConfig | None = None
    googlechat: ExtensionChannelConfig | None = None
    imessage: ExtensionChannelConfig | None = None
    irc: ExtensionChannelConfig | None = None
    msteams: ExtensionChannelConfig | None = None
    signal: ExtensionChannelConfig | None = None
    slack: ExtensionChannelConfig | None = None
    telegram: ExtensionChannelConfig | None = None
    whatsapp: ExtensionChannelConfig | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}
