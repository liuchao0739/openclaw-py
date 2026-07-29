"""SecretRef-aware Gateway config string resolver.

Mirrors src/gateway/resolve-configured-secret-input-string.ts.
"""

from __future__ import annotations

from typing import Any

SecretInputUnresolvedReasonStyle = Any

async def resolve_configured_secret_input_string(*args: Any, **kwargs: Any) -> Any: ...
async def resolve_configured_secret_input_with_fallback(*args: Any, **kwargs: Any) -> Any: ...
async def resolve_required_configured_secret_ref_input_string(*args: Any, **kwargs: Any) -> Any: ...
