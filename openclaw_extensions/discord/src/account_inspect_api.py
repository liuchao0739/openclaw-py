from typing import Any, Dict


async def inspect_discord_read_only_account(params: Dict[str, Any]) -> Dict[str, Any]:
    from .account_inspect import inspect_discord_account

    result = await inspect_discord_account(params)
    return {
        "accountId": result.accountId,
        "ok": result.ok,
        "error": result.error,
    }
