from typing import Any, Dict, Optional


class DiscordPluralKitConfig:
    def __init__(self, enabled: bool = False, api_token: Optional[str] = None):
        self.enabled = enabled
        self.apiToken = api_token


class PluralKitMemberInfo:
    def __init__(self, id: str, name: str = ""):
        self.id = id
        self.name = name


class PluralKitSystemInfo:
    def __init__(self, id: str, name: str = ""):
        self.id = id
        self.name = name


class PluralKitMessageInfo:
    def __init__(self, system: Optional[PluralKitSystemInfo] = None, member: Optional[PluralKitMemberInfo] = None):
        self.system = system
        self.member = member


async def fetch_plural_kit_message_info(message_id: str, config: Optional[DiscordPluralKitConfig] = None) -> Optional[PluralKitMessageInfo]:
    if not config or not config.enabled:
        return None
    try:
        import aiohttp

        async with aiohttp.ClientSession() as session:
            async with session.get(
                f"https://api.pluralkit.me/v2/messages/{message_id}"
            ) as response:
                if response.status >= 400:
                    return None
                data = await response.json()
                system = PluralKitSystemInfo(
                    id=data.get("system", ""),
                    name=data.get("system_name", ""),
                )
                member = PluralKitMemberInfo(
                    id=data.get("member", ""),
                    name=data.get("member_name", ""),
                )
                return PluralKitMessageInfo(system=system, member=member)
    except Exception:
        return None
