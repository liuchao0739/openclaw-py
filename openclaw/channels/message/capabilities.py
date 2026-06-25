"""Channel message capability derivation.

Computes durable-final delivery requirements from a concrete outbound payload.
"""

from __future__ import annotations

from typing import Any


def _has_media_payload(payload: dict[str, Any]) -> bool:
    media_url = payload.get("mediaUrl")
    if media_url and isinstance(media_url, str) and media_url.strip():
        return True
    media_urls = payload.get("mediaUrls")
    if isinstance(media_urls, list):
        return any(isinstance(url, str) and url.strip() for url in media_urls)
    return False


def _set_required(
    requirements: dict[str, bool],
    capability: str,
    required: bool | None,
) -> None:
    if required is True:
        requirements[capability] = True


def derive_durable_final_delivery_requirements(
    params: dict[str, Any],
) -> dict[str, bool]:
    """Derive the adapter capabilities needed before durable final delivery can be required."""
    requirements: dict[str, bool] = {}
    payload = params.get("payload", {})

    _set_required(requirements, "text", True)
    _set_required(requirements, "media", _has_media_payload(payload))
    _set_required(
        requirements,
        "replyTo",
        params.get("replyToId") is not None or payload.get("replyToId") is not None,
    )
    _set_required(requirements, "thread", params.get("threadId") is not None)
    _set_required(requirements, "silent", params.get("silent"))
    _set_required(requirements, "messageSendingHooks", params.get("messageSendingHooks") is not False)
    _set_required(requirements, "payload", params.get("payloadTransport"))
    _set_required(requirements, "batch", params.get("batch"))
    _set_required(requirements, "reconcileUnknownSend", params.get("reconcileUnknownSend"))
    _set_required(requirements, "afterSendSuccess", params.get("afterSendSuccess"))
    _set_required(requirements, "afterCommit", params.get("afterCommit"))

    extra = params.get("extraCapabilities", {})
    if isinstance(extra, dict):
        for capability, required in extra.items():
            _set_required(requirements, capability, required)

    return requirements
