import asyncio
import re
from typing import Any, Dict, List, Optional

from .accounts import (
    list_discord_account_ids,
    resolve_discord_account,
    ResolvedDiscordAccount,
)
from .channel_api import (
    DEFAULT_ACCOUNT_ID,
    PAIRING_APPROVED_MESSAGE,
    build_token_channel_status_summary,
    project_credential_snapshot_fields,
    resolve_configured_from_credential_statuses,
)
from .normalize import looks_like_discord_target_id, normalize_discord_messaging_target
from .runtime import get_discord_runtime
from .shared import create_discord_plugin_base, discord_config_adapter
from .target_parsing import parse_discord_target


DISCORD_ACCOUNT_STARTUP_STAGGER_MS = 10_000


def start_discord_startup_probe(params: Dict[str, Any]) -> None:
    async def run_probe():
        try:
            from .probe import probe_discord

            probe = await probe_discord(
                params["token"], 2500, {"includeApplication": True}
            )
            if params["abortSignal"] and params["abortSignal"].get("aborted"):
                return
            params["setStatus"](
                {
                    "accountId": params["accountId"],
                    "bot": probe.get("bot"),
                    "application": probe.get("application"),
                }
            )
            if probe.get("ok"):
                username = (probe.get("bot") or {}).get("username", "").strip()
                if username and params.get("log"):
                    params["log"].get("info", lambda msg: None)(
                        f'[{params["accountId"]}] Discord bot probe resolved @{username}'
                    )
            message_content = (probe.get("application") or {}).get("intents", {}).get("messageContent")
            if message_content == "disabled" and params.get("log"):
                params["log"].get("warn", lambda msg: None)(
                    f'[{params["accountId"]}] Discord Message Content Intent is disabled; bot may not respond to channel messages. Enable it in Discord Dev Portal (Bot → Privileged Gateway Intents) or require mentions.'
                )
        except Exception as err:
            if not (params["abortSignal"] and params["abortSignal"].get("aborted")):
                params["setStatus"](
                    {"accountId": params["accountId"], "bot": None, "application": None}
                )

    asyncio.ensure_future(run_probe())


def should_treat_discord_delivered_text_as_visible(params: Dict[str, Any]) -> bool:
    return (
        params.get("kind") == "block"
        and isinstance(params.get("text"), str)
        and len(params["text"].strip()) > 0
    )


def resolve_runtime_discord_message_actions() -> Optional[Dict[str, Any]]:
    try:
        runtime = get_discord_runtime()
        channel = runtime.get("channel") or {}
        return channel.get("discord", {}).get("messageActions")
    except Exception:
        return None


def resolve_discord_startup_delay_ms(cfg: Dict[str, Any], account_id: str) -> int:
    startup_account_ids = [
        candidate_id
        for candidate_id in list_discord_account_ids(cfg)
        if resolve_discord_account({"cfg": cfg, "accountId": candidate_id}).enabled
    ]
    try:
        startup_index = startup_account_ids.index(account_id)
    except ValueError:
        startup_index = -1
    return 0 if startup_index <= 0 else startup_index * DISCORD_ACCOUNT_STARTUP_STAGGER_MS


def format_discord_intents(intents: Optional[Dict[str, str]]) -> str:
    if not intents:
        return "unknown"
    return " ".join(
        [
            f'messageContent={intents.get("messageContent", "unknown")}',
            f'guildMembers={intents.get("guildMembers", "unknown")}',
            f'presence={intents.get("presence", "unknown")}',
        ]
    )


def to_conversation_lifecycle_binding(binding: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "boundAt": binding["boundAt"],
        "lastActivityAt": binding.get("lastActivityAt", binding["boundAt"]),
        "idleTimeoutMs": binding.get("idleTimeoutMs"),
        "maxAgeMs": binding.get("maxAgeMs"),
    }


discord_plugin: Dict[str, Any] = {
    "base": create_discord_plugin_base({"setup": None}),
    "pairing": {
        "text": {
            "idLabel": "discordUserId",
            "message": PAIRING_APPROVED_MESSAGE,
        }
    },
    "threading": {
        "scopedAccountReplyToMode": {
            "resolveAccount": lambda cfg, account_id: resolve_discord_account(
                {"cfg": cfg, "accountId": account_id}
            ),
            "resolveReplyToMode": lambda account: account.config.get("replyToMode"),
            "fallback": "off",
        }
    },
    "outbound": {
        "preferFinalAssistantVisibleText": True,
        "shouldTreatDeliveredTextAsVisible": should_treat_discord_delivered_text_as_visible,
    },
}
