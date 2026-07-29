from typing import Any, Dict, Optional

from .accounts import (
    is_discord_account_enabled_for_runtime,
    list_discord_account_ids,
    merge_discord_account_config,
    resolve_default_discord_account_id,
    resolve_discord_account,
    resolve_discord_account_allow_from,
    resolve_discord_account_disabled_reason,
    ResolvedDiscordAccount,
)
from .channel_api import (
    get_chat_channel_meta,
    resolve_configured_from_credential_statuses,
)
from .token import DEFAULT_ACCOUNT_ID, normalize_account_id, resolve_account_entry


DISCORD_CHANNEL = "discord"


def describe_account_snapshot(params: Dict[str, Any]) -> Dict[str, Any]:
    account = params["account"]
    configured = params.get("configured", False)
    extra = params.get("extra") or {}
    return {
        "accountId": account.accountId,
        "name": account.name,
        "enabled": account.enabled,
        "configured": configured,
        "extra": extra,
    }


def format_allow_from_lowercase(params: Dict[str, Any]) -> Any:
    allow_from = params.get("allowFrom") or []
    return [str(entry).lower() for entry in allow_from]


class DiscordConfigAdapter:
    def __init__(self, config: Dict[str, Any]):
        self.config = config

    def has_configured_state(self, env: Optional[Dict[str, str]] = None) -> bool:
        if not env:
            return False
        token = env.get("DISCORD_BOT_TOKEN")
        return isinstance(token, str) and len(token.strip()) > 0

    def is_enabled(self, account: ResolvedDiscordAccount, cfg: Dict[str, Any]) -> bool:
        return is_discord_account_enabled_for_runtime(account, cfg)

    def disabled_reason(self, account: ResolvedDiscordAccount, cfg: Dict[str, Any]) -> str:
        return resolve_discord_account_disabled_reason(account, cfg)

    def is_configured(self, account: ResolvedDiscordAccount) -> bool:
        configured = resolve_configured_from_credential_statuses(account)
        return configured if configured is not None else bool((account.token or "").strip())

    def describe_account(self, account: ResolvedDiscordAccount) -> Dict[str, Any]:
        configured = resolve_configured_from_credential_statuses(account)
        return describe_account_snapshot(
            {
                "account": account,
                "configured": configured if configured is not None else bool((account.token or "").strip()),
                "extra": {
                    "tokenSource": account.tokenSource,
                    "tokenStatus": account.tokenStatus,
                },
            }
        )


discord_config_adapter = DiscordConfigAdapter({"sectionKey": DISCORD_CHANNEL})


def create_discord_plugin_base(params: Dict[str, Any]) -> Dict[str, Any]:
    setup = params["setup"]
    base = {
        "id": DISCORD_CHANNEL,
        "meta": dict(get_chat_channel_meta(DISCORD_CHANNEL)),
        "capabilities": {
            "chatTypes": ["direct", "channel", "thread"],
            "polls": True,
            "reactions": True,
            "threads": True,
            "media": True,
            "tts": {"voice": {"synthesisTarget": "voice-note"}},
            "nativeCommands": True,
        },
        "commands": {
            "nativeCommandsAutoEnabled": True,
            "nativeSkillsAutoEnabled": True,
            "resolveNativeCommandName": lambda ctx: "voice" if ctx.get("commandKey") == "tts" else ctx.get("defaultName"),
        },
        "streaming": {"blockStreamingCoalesceDefaults": {"minChars": 1500, "idleMs": 1000}},
        "reload": {"configPrefixes": ["channels.discord"]},
        "config": discord_config_adapter,
        "messaging": {},
        "security": None,
        "secrets": {},
        "setup": setup,
    }
    if params.get("setupWizard"):
        base["setupWizard"] = params["setupWizard"]
    return base
