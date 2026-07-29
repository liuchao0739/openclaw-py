from typing import Any, Dict, Optional


class InspectedDiscordAccount:
    def __init__(self, account_id: str, token: str, ok: bool, error: Optional[str] = None):
        self.accountId = account_id
        self.token = token
        self.ok = ok
        self.error = error


async def inspect_discord_account(params: Dict[str, Any]) -> InspectedDiscordAccount:
    from .probe import probe_discord

    account_id = params.get("accountId", "default")
    token = params.get("token", "")
    try:
        probe = await probe_discord(token, 5000, {"includeApplication": True})
        return InspectedDiscordAccount(
            account_id=account_id,
            token=token,
            ok=probe.get("ok", False),
            error=probe.get("error"),
        )
    except Exception as err:
        return InspectedDiscordAccount(
            account_id=account_id, token=token, ok=False, error=str(err)
        )
