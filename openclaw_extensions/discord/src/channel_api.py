from typing import Any, Dict, Optional


DEFAULT_ACCOUNT_ID = "default"
PAIRING_APPROVED_MESSAGE = "Pairing approved. You can now message me directly."

DISCORD_CHANNEL_META = {
    "id": "discord",
    "label": "Discord",
    "selectionLabel": "Discord (Bot API)",
    "detailLabel": "Discord Bot",
    "docsPath": "/channels/discord",
    "docsLabel": "discord",
    "blurb": "very well supported right now.",
    "systemImage": "bubble.left.and.bubble.right",
    "markdownCapable": True,
    "preferSessionLookupForAnnounceTarget": True,
}


def get_chat_channel_meta(id_value: str) -> Dict[str, Any]:
    if id_value != DISCORD_CHANNEL_META["id"]:
        raise ValueError(f"Unsupported Discord channel meta lookup: {id_value}")
    return DISCORD_CHANNEL_META


def build_token_channel_status_summary(snapshot: Any, options: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    include_mode = (options or {}).get("includeMode", False)
    summary: Dict[str, Any] = {
        "accountId": getattr(snapshot, "accountId", None) if not isinstance(snapshot, dict) else snapshot.get("accountId"),
        "connected": getattr(snapshot, "connected", False) if not isinstance(snapshot, dict) else snapshot.get("connected", False),
    }
    if include_mode:
        summary["mode"] = getattr(snapshot, "mode", None) if not isinstance(snapshot, dict) else snapshot.get("mode")
    return summary


def project_credential_snapshot_fields(account: Any) -> Dict[str, Any]:
    return {
        "tokenSource": getattr(account, "tokenSource", None) if not isinstance(account, dict) else account.get("tokenSource"),
        "tokenStatus": getattr(account, "tokenStatus", None) if not isinstance(account, dict) else account.get("tokenStatus"),
    }


def resolve_configured_from_credential_statuses(account: Any) -> Optional[bool]:
    token_status = (
        getattr(account, "tokenStatus", None)
        if not isinstance(account, dict)
        else account.get("tokenStatus")
    )
    if token_status == "available":
        return True
    if token_status in ("configured_unavailable", "missing"):
        return False
    return None
