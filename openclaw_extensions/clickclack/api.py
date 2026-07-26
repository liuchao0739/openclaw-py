"""Public ClickClack runtime API barrel used by plugin tests, docs, and integration code."""

from openclaw_extensions.clickclack.src.accounts import (
    DEFAULT_ACCOUNT_ID,
    list_click_clack_account_ids,
    list_enabled_click_clack_accounts,
    resolve_click_clack_account,
    resolve_default_click_clack_account_id,
)
from openclaw_extensions.clickclack.src.channel import click_clack_plugin
from openclaw_extensions.clickclack.src.config_schema import click_clack_config_schema
from openclaw_extensions.clickclack.src.http_client import create_click_clack_client
from openclaw_extensions.clickclack.src.runtime import (
    get_click_clack_runtime,
    set_click_clack_runtime,
)
from openclaw_extensions.clickclack.src.target import (
    build_click_clack_target,
    parse_click_clack_target,
)
from openclaw_extensions.clickclack.src.types import (
    ClickClackAccountConfig,
    ClickClackEvent,
    ClickClackMessage,
    ClickClackTarget,
    CoreConfig,
    ResolvedClickClackAccount,
)

__all__ = [
    "DEFAULT_ACCOUNT_ID",
    "ClickClackAccountConfig",
    "ClickClackEvent",
    "ClickClackMessage",
    "ClickClackTarget",
    "CoreConfig",
    "ResolvedClickClackAccount",
    "build_click_clack_target",
    "click_clack_config_schema",
    "click_clack_plugin",
    "create_click_clack_client",
    "get_click_clack_runtime",
    "list_click_clack_account_ids",
    "list_enabled_click_clack_accounts",
    "parse_click_clack_target",
    "resolve_click_clack_account",
    "resolve_default_click_clack_account_id",
    "set_click_clack_runtime",
]
