"""Commands/onboard-non-interactive — config write and remote setup."""

from openclaw.commands.onboard_non_interactive.config_write import (
    commit_non_interactive_onboard_config,
)
from openclaw.commands.onboard_non_interactive.remote import (
    run_non_interactive_remote_setup,
)

__all__ = [
    "commit_non_interactive_onboard_config",
    "run_non_interactive_remote_setup",
]
