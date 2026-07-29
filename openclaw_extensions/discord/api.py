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
from .src.directory_config import (
    list_discord_directory_groups_from_config,
    list_discord_directory_peers_from_config,
)
from .src.group_policy import (
    resolve_discord_group_require_mention,
    resolve_discord_group_tool_policy,
)
from .src.normalize import (
    looks_like_discord_target_id,
    normalize_discord_messaging_target,
    normalize_discord_outbound_target,
)
from .src.status_issues import collect_discord_status_issues
from .src.components import (
    build_discord_component_custom_id,
    build_discord_component_message_flags,
    build_discord_interactive_components,
    build_discord_modal_custom_id,
    create_discord_form_modal,
    DISCORD_COMPONENT_ATTACHMENT_PREFIX,
    DISCORD_COMPONENT_CUSTOM_ID_KEY,
    DISCORD_MODAL_CUSTOM_ID_KEY,
    DiscordFormModal,
    format_discord_component_event_text,
    parse_discord_component_custom_id,
    parse_discord_component_custom_id_for_interaction,
    parse_discord_modal_custom_id,
    parse_discord_modal_custom_id_for_interaction,
    read_discord_component_spec,
    resolve_discord_component_attachment_name,
)
from .src.exec_approvals import (
    get_discord_exec_approval_approvers,
    is_discord_exec_approval_approver,
    is_discord_exec_approval_client_enabled,
    should_suppress_local_discord_exec_approval_prompt,
)
from .src.pluralkit import (
    DiscordPluralKitConfig,
    fetch_plural_kit_message_info,
    PluralKitMemberInfo,
    PluralKitMessageInfo,
    PluralKitSystemInfo,
)
from .src.probe import (
    fetch_discord_application_id,
    fetch_discord_application_summary,
    parse_application_id_from_token,
    probe_discord,
    resolve_discord_privileged_intents_from_flags,
    DiscordApplicationSummary,
    DiscordPrivilegedIntentsSummary,
    DiscordPrivilegedIntentStatus,
    DiscordProbe,
)
from .src.session_key_normalization import normalize_explicit_discord_session_key
from .src.send_target_parsing import parse_discord_send_target, SendDiscordTarget
from .src.targets import (
    parse_discord_target,
    resolve_discord_channel_id,
    resolve_discord_target,
    DiscordTarget,
    DiscordTargetKind,
    DiscordTargetParseOptions,
)
from .src.security_audit import collect_discord_security_audit_findings
from .src.monitor.timeouts import (
    DISCORD_ATTACHMENT_IDLE_TIMEOUT_MS,
    DISCORD_ATTACHMENT_TOTAL_TIMEOUT_MS,
    DISCORD_DEFAULT_INBOUND_WORKER_TIMEOUT_MS,
    DISCORD_DEFAULT_LISTENER_TIMEOUT_MS,
    merge_abort_signals,
)


async def handle_discord_message_action(*args, **kwargs):
    from .src.channel_actions_runtime import handle_discord_message_action as impl
    return await impl(*args, **kwargs)
