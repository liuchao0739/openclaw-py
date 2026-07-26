"""Google Chat channel adapters.

Mirrors extensions/googlechat/src/channel.adapters.ts (directory surface).
"""

from __future__ import annotations

from openclaw.channels.plugins.directory_adapters import create_channel_directory_adapter
from openclaw.channels.plugins.directory_config_helpers import (
    list_resolved_directory_group_entries_from_map_keys,
    list_resolved_directory_user_entries_from_allow_from,
)
from openclaw.plugin_sdk.channel_config_helpers import adapt_scoped_account_accessor
from openclaw_extensions.googlechat.src.accounts import (
    ResolvedGoogleChatAccount,
    resolve_google_chat_account,
)
from openclaw_extensions.googlechat.src.targets import normalize_google_chat_target


async def _list_google_chat_peers(params: dict) -> list[dict[str, str]]:
    return list_resolved_directory_user_entries_from_allow_from(
        cfg=params["cfg"],
        account_id=params.get("accountId"),
        query=params.get("query"),
        limit=params.get("limit"),
        resolve_account=adapt_scoped_account_accessor(
            lambda params: resolve_google_chat_account(
                cfg=params["cfg"],
                account_id=params.get("accountId"),
            )
        ),
        resolve_allow_from=lambda account: (account.config.get("dm") or {}).get("allowFrom"),
        normalize_id=lambda entry: normalize_google_chat_target(entry) or entry,
    )


async def _list_google_chat_groups(params: dict) -> list[dict[str, str]]:
    return list_resolved_directory_group_entries_from_map_keys(
        cfg=params["cfg"],
        account_id=params.get("accountId"),
        query=params.get("query"),
        limit=params.get("limit"),
        resolve_account=adapt_scoped_account_accessor(
            lambda params: resolve_google_chat_account(
                cfg=params["cfg"],
                account_id=params.get("accountId"),
            )
        ),
        resolve_groups=lambda account: account.config.get("groups"),
    )


googlechat_directory_adapter = create_channel_directory_adapter(
    list_peers=_list_google_chat_peers,
    list_groups=_list_google_chat_groups,
)

__all__ = ["ResolvedGoogleChatAccount", "googlechat_directory_adapter"]
