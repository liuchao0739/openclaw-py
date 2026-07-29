from copy import deepcopy
from typing import Any

from .accounts import (
    DEFAULT_ACCOUNT_ID,
    inspect_feishu_credentials,
    list_enabled_feishu_accounts,
    list_feishu_account_ids,
    resolve_default_feishu_account_id,
    resolve_default_feishu_account_selection,
    resolve_feishu_account,
    resolve_feishu_runtime_account,
)
from .conversation_id import build_feishu_model_override_parent_candidates
from .manifest import MANIFEST
from .setup_core import feishu_setup_adapter, set_feishu_named_account_enabled
from .setup_surface import feishu_setup_wizard, run_feishu_login
from .types import FeishuConfig, FeishuProbeResult, ResolvedFeishuAccount


def _resolve_group_tool_policy(params: dict) -> dict:
    return {"allowed": True}


def _message_tool_hints() -> list:
    return [
        "- Feishu targeting: omit `target` to reply to the current conversation (auto-inferred). Explicit targets: `user:open_id` or `chat:chat_id`.",
        "- Feishu supports interactive cards plus native image, file, audio, and video/media delivery.",
        "- Feishu supports `send`, `read`, `edit`, `thread-reply`, pins, and channel/member lookup, plus reactions when enabled.",
    ]


def _set_account_enabled(params: dict) -> Any:
    cfg = params.get("cfg", {})
    account_id = params.get("accountId")
    enabled = params.get("enabled")
    if account_id == DEFAULT_ACCOUNT_ID:
        if not isinstance(cfg, dict):
            cfg = {}
        result = deepcopy(cfg)
        channels = result.setdefault("channels", {})
        feishu_cfg = channels.get("feishu", {})
        if not isinstance(feishu_cfg, dict):
            feishu_cfg = {}
        feishu_cfg["enabled"] = enabled
        channels["feishu"] = feishu_cfg
        result["channels"] = channels
        return result
    return set_feishu_named_account_enabled(cfg, account_id, enabled)


def _delete_account(params: dict) -> Any:
    cfg = params.get("cfg", {})
    account_id = params.get("accountId")
    if account_id == DEFAULT_ACCOUNT_ID:
        if not isinstance(cfg, dict):
            return cfg
        result = deepcopy(cfg)
        channels = dict(result.get("channels") or {})
        channels.pop("feishu", None)
        if channels:
            result["channels"] = channels
        else:
            result.pop("channels", None)
        return result
    if not isinstance(cfg, dict):
        return cfg
    result = deepcopy(cfg)
    channels = result.setdefault("channels", {})
    feishu_cfg = channels.get("feishu", {})
    if not isinstance(feishu_cfg, dict):
        feishu_cfg = {}
    accounts = dict(feishu_cfg.get("accounts") or {})
    accounts.pop(account_id, None)
    if accounts:
        feishu_cfg["accounts"] = accounts
    else:
        feishu_cfg.pop("accounts", None)
    channels["feishu"] = feishu_cfg
    result["channels"] = channels
    return result


feishu_config_adapter = {
    "listAccountIds": lambda cfg: list_feishu_account_ids(cfg),
    "resolveDefaultAccountId": lambda cfg: resolve_default_feishu_account_id(cfg),
    "resolveAccount": lambda params: resolve_feishu_account(params),
    "resolveRuntimeAccount": lambda params, options=None: resolve_feishu_runtime_account(params, options),
    "listEnabledAccounts": lambda cfg: list_enabled_feishu_accounts(cfg),
    "setAccountEnabled": _set_account_enabled,
    "deleteAccount": _delete_account,
}


feishu_plugin = {
    "base": {
        "id": "feishu",
        "meta": {
            "id": MANIFEST["id"],
            "name": MANIFEST["name"],
            "description": MANIFEST["description"],
            "aliases": MANIFEST["channel"]["aliases"],
        },
        "capabilities": {
            "chatTypes": ["direct", "channel"],
            "polls": False,
            "threads": True,
            "media": True,
            "tts": {
                "voice": {
                    "synthesisTarget": "voice-note",
                    "transcodesAudio": True,
                },
            },
            "reactions": True,
            "edit": True,
            "reply": True,
        },
        "agentPrompt": {
            "messageToolHints": _message_tool_hints,
        },
        "groups": {
            "resolveToolPolicy": _resolve_group_tool_policy,
        },
        "conversationBindings": {
            "defaultTopLevelPlacement": "current",
            "buildModelOverrideParentCandidates": lambda params: build_feishu_model_override_parent_candidates((params or {}).get("parentConversationId")),
        },
        "mentions": {
            "stripPatterns": lambda: ['<at user_id="[^"]*">[^<]*</at>'],
        },
        "reload": {"configPrefixes": ["channels.feishu"]},
        "config": feishu_config_adapter,
    },
    "setup": {
        "adapter": feishu_setup_adapter,
        "wizard": feishu_setup_wizard,
        "login": run_feishu_login,
    },
    "channelEnvVars": MANIFEST["channelEnvVars"]["feishu"],
}
