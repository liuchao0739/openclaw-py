"""Gateway node pairing auto-approval policy.

Mirrors src/gateway/node-pairing-auto-approve.ts.
"""

from __future__ import annotations

from typing import Any

NodePairingAutoApproveReason = Any

def resolve_node_pairing_client_ip_source(*args: Any, **kwargs: Any) -> Any: ...
def should_auto_approve_node_pairing_from_trusted_cidrs(*args: Any, **kwargs: Any) -> Any: ...
