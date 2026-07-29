from typing import Any, Dict, Optional


async def inspect_discord_account_token(token: str) -> Dict[str, Any]:
    from .probe import parse_application_id_from_token, fetch_discord_application_summary

    application_id = parse_application_id_from_token(token)
    application: Optional[Any] = None
    if application_id is None:
        application = await fetch_discord_application_summary(token)
        application_id = application.id if application else None
    return {
        "applicationId": application_id,
        "application": application,
    }
