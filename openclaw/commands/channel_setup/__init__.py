"""Commands/channel-setup — setup wizard registry and types."""

from openclaw.commands.channel_setup.registry import (
    resolve_channel_setup_wizard_adapter_for_plugin,
)
from openclaw.commands.channel_setup.types import ChannelSetupWizardAdapter

__all__ = [
    "ChannelSetupWizardAdapter",
    "resolve_channel_setup_wizard_adapter_for_plugin",
]
