"""Gateway hook mapping resolver.

Mirrors src/gateway/hooks-mapping.ts.
"""

from __future__ import annotations

from typing import Any

HookMappingResolved = Any

def resolve_hook_mappings(*args: Any, **kwargs: Any) -> Any: ...
def has_hook_template_expressions(*args: Any, **kwargs: Any) -> Any: ...
async def apply_hook_mappings(*args: Any, **kwargs: Any) -> Any: ...
