"""Delivery-result adapters for channel turn receipts."""

from __future__ import annotations

from typing import Any


def _list_message_receipt_platform_ids(receipt: dict[str, Any]) -> list[str]:
    """Extract platform message IDs from a receipt."""
    ids: list[str] = []
    if isinstance(receipt, dict):
        msg_id = receipt.get("messageId")
        if msg_id and isinstance(msg_id, str):
            ids.append(msg_id)
        batch_ids = receipt.get("messageIds")
        if isinstance(batch_ids, list):
            ids.extend(mid for mid in batch_ids if isinstance(mid, str))
    return ids


def create_channel_delivery_result_from_receipt(
    receipt: dict[str, Any],
    thread_id: str | None = None,
    reply_to_id: str | None = None,
    visible_reply_sent: bool | None = None,
    delivery_intent: str | None = None,
) -> dict[str, Any]:
    """Convert a normalized message receipt into the delivery result shape used by channel turns."""
    message_ids = _list_message_receipt_platform_ids(receipt)
    result: dict[str, Any] = {"receipt": receipt}
    if message_ids:
        result["messageIds"] = message_ids
    if thread_id:
        result["threadId"] = thread_id
    if reply_to_id:
        result["replyToId"] = reply_to_id
    if visible_reply_sent is not None:
        result["visibleReplySent"] = visible_reply_sent
    if delivery_intent:
        result["deliveryIntent"] = delivery_intent
    return result
