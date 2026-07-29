import re
from typing import Any, Dict, Optional

from .api import fetch_discord


class DiscordPrivilegedIntentStatus:
    def __init__(self, name: str, status: str):
        self.name = name
        self.status = status


class DiscordPrivilegedIntentsSummary:
    def __init__(
        self,
        message_content: DiscordPrivilegedIntentStatus,
        guild_members: DiscordPrivilegedIntentStatus,
        presence: DiscordPrivilegedIntentStatus,
    ):
        self.messageContent = message_content
        self.guildMembers = guild_members
        self.presence = presence


class DiscordApplicationSummary:
    def __init__(self, id: str, name: str = "", intents: Optional[DiscordPrivilegedIntentsSummary] = None):
        self.id = id
        self.name = name
        self.intents = intents


class DiscordProbe:
    def __init__(
        self,
        ok: bool,
        status: Optional[int] = None,
        bot: Optional[Dict[str, Any]] = None,
        application: Optional[DiscordApplicationSummary] = None,
        error: Optional[str] = None,
    ):
        self.ok = ok
        self.status = status
        self.bot = bot
        self.application = application
        self.error = error

    def to_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.ok,
            "status": self.status,
            "bot": self.bot,
            "application": self.application,
            "error": self.error,
        }


def parse_application_id_from_token(token: str) -> Optional[str]:
    try:
        first_segment = token.split(".")[0]
        import base64

        padded = first_segment + "=" * (-len(first_segment) % 4)
        decoded = base64.b64decode(padded)
        return decoded.decode("utf-8")
    except Exception:
        return None


def resolve_discord_privileged_intents_from_flags(flags: Optional[int]) -> DiscordPrivilegedIntentsSummary:
    flags_value = flags or 0
    message_content_enabled = bool(flags_value & (1 << 19))
    guild_members_enabled = bool(flags_value & (1 << 1))
    presence_enabled = bool(flags_value & (1 << 8))
    return DiscordPrivilegedIntentsSummary(
        message_content=DiscordPrivilegedIntentStatus(
            "messageContent", "enabled" if message_content_enabled else "disabled"
        ),
        guild_members=DiscordPrivilegedIntentStatus(
            "guildMembers", "enabled" if guild_members_enabled else "disabled"
        ),
        presence=DiscordPrivilegedIntentStatus(
            "presence", "enabled" if presence_enabled else "disabled"
        ),
    )


async def fetch_discord_application_id(token: str) -> Optional[str]:
    parsed = parse_application_id_from_token(token)
    if parsed:
        return parsed
    try:
        app = await fetch_discord_application_summary(token)
        return app.id if app else None
    except Exception:
        return None


async def fetch_discord_application_summary(token: str) -> Optional[DiscordApplicationSummary]:
    try:
        data = await fetch_discord("/users/@me", token)
        if not data or not data.get("id"):
            return None
        flags = data.get("flags")
        intents = resolve_discord_privileged_intents_from_flags(flags)
        return DiscordApplicationSummary(
            id=data["id"], name=data.get("username", ""), intents=intents
        )
    except Exception:
        return None


async def probe_discord(
    token: str,
    timeout_ms: int = 5000,
    options: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    options = options or {}
    if not token or not token.strip():
        return {"ok": False, "error": "missing token"}
    try:
        data = await fetch_discord("/users/@me", token)
        if not data or not data.get("id"):
            return {"ok": False, "error": "no bot user returned"}
        bot = {
            "id": data.get("id"),
            "username": data.get("username", ""),
        }
        application: Optional[DiscordApplicationSummary] = None
        if options.get("includeApplication"):
            application = await fetch_discord_application_summary(token)
        return {
            "ok": True,
            "status": 200,
            "bot": bot,
            "application": application,
        }
    except Exception as err:
        return {"ok": False, "error": str(err)}
