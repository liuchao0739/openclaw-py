"""Session patch applier for gateway session metadata and model/runtime overrides.

Mirrors src/gateway/sessions-patch.ts.
"""

from __future__ import annotations

from typing import Any

async def project_sessions_patch_entry(*args: Any, **kwargs: Any) -> Any: ...
async def apply_sessions_patch_to_store(*args: Any, **kwargs: Any) -> Any: ...
