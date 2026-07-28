from __future__ import annotations

from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class ChannelDefaultsConfig(BaseModel):
    group_policy: Optional[str] = Field(default=None, alias="groupPolicy")
    context_visibility: Optional[str] = Field(default=None, alias="contextVisibility")
    heartbeat: Optional[Dict[str, Any]] = None
    bot_loop_protection: Optional[Dict[str, Any]] = Field(default=None, alias="botLoopProtection")

    model_config = {"populate_by_name": True}


class ExtensionNestedPolicyConfig(BaseModel):
    policy: Optional[str] = None
    allow_from: Optional[List[str | int]] = Field(default=None, alias="allowFrom")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExtensionAccountConfig(ExtensionNestedPolicyConfig):
    default_to: Optional[str | int] = Field(default=None, alias="defaultTo")
    dm_policy: Optional[str] = Field(default=None, alias="dmPolicy")
    dm: Optional[ExtensionNestedPolicyConfig] = None
    media_max_mb: Optional[int] = Field(default=None, alias="mediaMaxMb")
    config_writes: Optional[bool] = Field(default=None, alias="configWrites")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ExtensionChannelConfig(BaseModel):
    enabled: Optional[bool] = None
    allow_from: Optional[List[str | int]] = Field(default=None, alias="allowFrom")
    default_to: Optional[str | int] = Field(default=None, alias="defaultTo")
    default_account: Optional[str] = Field(default=None, alias="defaultAccount")
    dm_policy: Optional[str] = Field(default=None, alias="dmPolicy")
    group_policy: Optional[str] = Field(default=None, alias="groupPolicy")
    context_visibility: Optional[str] = Field(default=None, alias="contextVisibility")
    health_monitor: Optional[Dict[str, Any]] = Field(default=None, alias="healthMonitor")
    dm: Optional[ExtensionNestedPolicyConfig] = None
    network: Optional[Dict[str, Any]] = None
    groups: Optional[Dict[str, Any]] = None
    rooms: Optional[Dict[str, Any]] = None
    media_max_mb: Optional[int] = Field(default=None, alias="mediaMaxMb")
    callback_base_url: Optional[str] = Field(default=None, alias="callbackBaseUrl")
    interactions: Optional[Dict[str, Any]] = None
    exec_approvals: Optional[Dict[str, Any]] = Field(default=None, alias="execApprovals")
    thread_bindings: Optional[Dict[str, Any]] = Field(default=None, alias="threadBindings")
    bot_loop_protection: Optional[Dict[str, Any]] = Field(default=None, alias="botLoopProtection")
    dangerously_allow_private_network: Optional[bool] = Field(
        default=None, alias="dangerouslyAllowPrivateNetwork"
    )
    accounts: Optional[Dict[str, ExtensionAccountConfig]] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ChannelsConfig(BaseModel):
    defaults: Optional[ChannelDefaultsConfig] = None
    model_by_channel: Optional[Dict[str, Dict[str, str]]] = Field(
        default=None, alias="modelByChannel"
    )
    discord: Optional[ExtensionChannelConfig] = None
    googlechat: Optional[ExtensionChannelConfig] = None
    imessage: Optional[ExtensionChannelConfig] = None
    irc: Optional[ExtensionChannelConfig] = None
    msteams: Optional[ExtensionChannelConfig] = None
    signal: Optional[ExtensionChannelConfig] = None
    slack: Optional[ExtensionChannelConfig] = None
    telegram: Optional[ExtensionChannelConfig] = None
    whatsapp: Optional[ExtensionChannelConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}
