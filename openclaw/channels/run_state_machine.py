"""Channel run-state tracker used to publish busy/activity status.

Mirrors src/channels/run-state-machine.ts.
"""

from __future__ import annotations

from typing import Any

RunStateStatusSink = Any

def create_run_state_machine(*args: Any, **kwargs: Any) -> Any: ...
