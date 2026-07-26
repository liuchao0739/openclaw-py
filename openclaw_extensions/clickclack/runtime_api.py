"""Public runtime injection surface used by the bundled ClickClack entry."""

from openclaw_extensions.clickclack.api import (
    ClickClackAccountConfig,
    ClickClackEvent,
    ClickClackMessage,
    ClickClackTarget,
    ResolvedClickClackAccount,
    create_click_clack_client,
    parse_click_clack_target,
    resolve_click_clack_account,
    set_click_clack_runtime,
)

__all__ = [
    "ClickClackAccountConfig",
    "ClickClackEvent",
    "ClickClackMessage",
    "ClickClackTarget",
    "ResolvedClickClackAccount",
    "create_click_clack_client",
    "parse_click_clack_target",
    "resolve_click_clack_account",
    "set_click_clack_runtime",
]
