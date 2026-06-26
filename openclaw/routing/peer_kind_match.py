"""Peer kind matching helpers compare channel peer kinds against chat targets.

Mirrors src/routing/peer-kind-match.ts.
"""

from __future__ import annotations


def peer_kind_matches(binding_kind: str, scope_kind: str) -> bool:
    """Check if a binding peer kind matches a scope peer kind.

    Group and channel peers are treated as compatible because several chat
    platforms expose broadcast-like group spaces with either label.
    """
    if binding_kind == scope_kind:
        return True
    return (
        (binding_kind == "group" and scope_kind == "channel")
        or (binding_kind == "channel" and scope_kind == "group")
    )
