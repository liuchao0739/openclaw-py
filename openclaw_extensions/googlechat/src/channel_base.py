from __future__ import annotations

from openclaw.plugin_sdk.account_helpers import describe_account_snapshot
from openclaw.plugin_sdk.allow_from import format_normalized_allow_from_entries
from openclaw.plugin_sdk.channel_config_helpers import (
    adapt_scoped_account_accessor,
    create_scoped_channel_config_adapter,
)
from openclaw.plugin_sdk.string_coerce_runtime import normalize_lowercase_string_or_empty
from openclaw_extensions.googlechat.src.accounts import (
    GoogleChatConfigAccessorAccount,
    ResolvedGoogleChatAccount,
    list_google_chat_account_ids,
    resolve_default_google_chat_account_id,
    resolve_google_chat_account,
    resolve_google_chat_config_accessor_account,
)
from openclaw_extensions.googlechat.src.setup_core import googlechat_setup_adapter
from openclaw_extensions.googlechat.src.setup_surface import googlechat_setup_wizard

GOOGLECHAT_CHANNEL_ID = "googlechat"

googlechat_meta = {
    "id": GOOGLECHAT_CHANNEL_ID,
    "label": "Google Chat",
    "selection_label": "Google Chat (Chat API)",
    "docs_path": "/channels/googlechat",
    "docs_label": "googlechat",
    "blurb": "Google Workspace Chat app with HTTP webhook.",
    "aliases": ["gchat", "google-chat"],
    "order": 55,
    "detail_label": "Google Chat",
    "system_image": "message.badge",
    "markdown_capable": True,
}


def format_google_chat_allow_from_entry(entry: str) -> str:
    return normalize_lowercase_string_or_empty(
        entry
        .strip()
        .replace(r"^(googlechat|google-chat|gchat):", "")
        .replace(r"^user:", "")
        .replace(r"^users/", "")
    )


google_chat_config_adapter = create_scoped_channel_config_adapter(
    section_key=GOOGLECHAT_CHANNEL_ID,
    list_account_ids=list_google_chat_account_ids,
    resolve_account=adapt_scoped_account_accessor(resolve_google_chat_account),
    resolve_accessor_account=resolve_google_chat_config_accessor_account,
    default_account_id=resolve_default_google_chat_account_id,
    clear_base_fields=[
        "serviceAccount",
        "serviceAccountFile",
        "audienceType",
        "audience",
        "webhookPath",
        "webhookUrl",
        "botUser",
        "name",
    ],
    resolve_allow_from=lambda account: (account.config.get("dm") or {}).get("allowFrom"),
    format_allow_from=lambda allow_from: format_normalized_allow_from_entries({
        "allow_from": allow_from,
        "normalize_entry": format_google_chat_allow_from_entry,
    }),
    resolve_default_to=lambda account: account.config.get("defaultTo"),
)


def create_google_chat_plugin_base(params: dict | None = None) -> dict:
    if params is None:
        params = {}
    config_schema = params.get("configSchema")
    result = {
        "id": GOOGLECHAT_CHANNEL_ID,
        "meta": {**googlechat_meta},
        "setup": googlechat_setup_adapter,
        "setupWizard": googlechat_setup_wizard,
        "capabilities": {
            "chatTypes": ["direct", "group", "thread"],
            "reactions": True,
            "threads": True,
            "media": True,
            "nativeCommands": False,
            "blockStreaming": True,
        },
        "streaming": {
            "blockStreamingCoalesceDefaults": {"minChars": 1500, "idleMs": 1000},
        },
        "reload": {"configPrefixes": ["channels.googlechat"]},
        "config": {
            **google_chat_config_adapter,
            "isConfigured": lambda account: account.credential_source != "none",
            "describeAccount": lambda account: describe_account_snapshot({
                "account": account,
                "configured": account.credential_source != "none",
                "extra": {"credentialSource": account.credential_source},
            }),
        },
    }
    if config_schema:
        result["configSchema"] = config_schema
    return result


__all__ = [
    "GOOGLECHAT_CHANNEL_ID",
    "googlechat_meta",
    "create_google_chat_plugin_base",
    "format_google_chat_allow_from_entry",
    "google_chat_config_adapter",
]