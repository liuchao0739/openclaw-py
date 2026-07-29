"""Legacy direct-DM access resolver.

Mirrors src/channels/direct-dm-access.ts.
"""

from __future__ import annotations

from typing import Any

DirectDmCommandAuthorizationRuntime = Any
ResolvedInboundDirectDmAccess = Any

def create_pre_crypto_direct_dm_authorizer(*args: Any, **kwargs: Any) -> Any: ...
async def resolve_inbound_direct_dm_access_with_runtime(*args: Any, **kwargs: Any) -> Any: ...
