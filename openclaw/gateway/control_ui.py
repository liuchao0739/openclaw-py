"""Gateway Control UI HTTP handler.

Mirrors src/gateway/control-ui.ts.
"""

from __future__ import annotations

from typing import Any

ControlUiRootState = Any

def rewrite_control_ui_index_html_public_asset_hrefs(*args: Any, **kwargs: Any) -> Any: ...
async def handle_control_ui_assistant_media_request(*args: Any, **kwargs: Any) -> Any: ...
async def handle_control_ui_avatar_request(*args: Any, **kwargs: Any) -> Any: ...
async def handle_control_ui_http_request(*args: Any, **kwargs: Any) -> Any: ...
