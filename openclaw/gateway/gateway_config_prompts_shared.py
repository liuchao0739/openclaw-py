"""Gateway setup prompt shared constants.

Mirrors src/gateway/gateway-config-prompts.shared.ts.
"""

from __future__ import annotations

from typing import Any

TAILSCALE_EXPOSURE_OPTIONS: Any = None
TAILSCALE_MISSING_BIN_NOTE_LINES: Any = None
TAILSCALE_DOCS_LINES: Any = None

async def maybe_add_tailnet_origin_to_control_ui_allowed_origins(*args: Any, **kwargs: Any) -> Any: ...
