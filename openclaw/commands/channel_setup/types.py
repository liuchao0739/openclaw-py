"""Public setup wizard types re-exported for command/onboarding helpers."""

from __future__ import annotations

from typing import Any, Protocol


class ChannelSetupWizardAdapter(Protocol):
    """Adapter interface for channel setup wizards."""

    def get_status(self) -> dict[str, Any]: ...

    def configure(self, params: dict[str, Any]) -> Any: ...
