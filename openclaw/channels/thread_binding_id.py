"""Thread binding id parsing helpers for account-scoped conversation bindings."""

from __future__ import annotations


def resolve_thread_binding_conversation_id_from_binding_id(
    account_id: str,
    binding_id: str | None = None,
) -> str | None:
    """Parse an account-prefixed binding id back into a conversation id."""
    if not binding_id or not isinstance(binding_id, str):
        return None
    binding_id = binding_id.strip()
    if not binding_id:
        return None
    prefix = f"{account_id}:"
    if not binding_id.startswith(prefix):
        return None
    conversation_id = binding_id[len(prefix):].strip()
    return conversation_id or None
