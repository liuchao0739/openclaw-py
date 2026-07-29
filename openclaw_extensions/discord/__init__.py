from .src.channel import discord_plugin
from .src.channel_setup import discord_setup_plugin
from .src.subagent_hooks import (
    handle_discord_subagent_delivery_target,
    handle_discord_subagent_ended,
    handle_discord_subagent_spawning,
)
from .src.account_inspect import inspect_discord_account, InspectedDiscordAccount
from .src.token import DiscordCredentialStatus
from .src.accounts import (
    create_discord_action_gate,
    list_discord_account_ids,
    list_enabled_discord_accounts,
    merge_discord_account_config,
    ResolvedDiscordAccount,
    resolve_default_discord_account_id,
    resolve_discord_account,
    resolve_discord_account_config,
    resolve_discord_max_lines_per_message,
)
from .src.actions.handle_action_guild_admin import try_handle_discord_message_action_guild_admin
from .src.api import DiscordApiError, fetch_discord, request_discord
from .src.components import build_discord_component_message

CHANNEL_ID = "discord"
CHANNEL_NAME = "Discord"
CHANNEL_DESCRIPTION = "Discord channel plugin"


def define_bundled_channel_entry():
    return {
        "id": CHANNEL_ID,
        "name": CHANNEL_NAME,
        "description": CHANNEL_DESCRIPTION,
        "plugin": {"specifier": ".src.channel", "exportName": "discord_plugin"},
        "runtime": {"specifier": ".src.runtime_setter_api", "exportName": "set_discord_runtime"},
        "accountInspect": {
            "specifier": ".src.account_inspect_api",
            "exportName": "inspect_discord_read_only_account",
        },
    }


def register_full(api):
    from .src.subagent_hooks_api import register_discord_subagent_hooks
    from .src.transcripts_source_api import discord_voice_transcripts_source_provider

    register_discord_subagent_hooks(api)
    api.register_transcript_source_provider(discord_voice_transcripts_source_provider)


default_entry = define_bundled_channel_entry()
