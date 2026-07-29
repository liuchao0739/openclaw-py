from __future__ import annotations

from typing import Any

from openclaw.utils.account_id import normalize_account_id
from openclaw.utils.delivery_context_types import DeliveryContext, DeliveryContextSessionSource
from openclaw.utils.message_channel_constants import (
    INTERNAL_MESSAGE_CHANNEL,
    is_internal_non_delivery_channel,
)
from openclaw.utils.message_channel_core import (
    is_deliverable_message_channel,
    normalize_message_channel,
)


def _normalize_channel_route_target(params: Any) -> dict | None:
    channel = params.get("channel") if isinstance(params, dict) else None
    to = params.get("to") if isinstance(params, dict) else None
    account_id = params.get("accountId") if isinstance(params, dict) else None
    thread_id = params.get("threadId") if isinstance(params, dict) else None
    if not channel and not to:
        return None
    result: dict[str, Any] = {}
    if channel:
        result["channel"] = channel
    if to:
        result["to"] = to
    if account_id:
        result["accountId"] = account_id
    if thread_id is not None:
        result["threadId"] = thread_id
    return result or None


def _normalize_channel_route_ref(params: Any) -> dict | None:
    if not isinstance(params, dict):
        return None
    channel = params.get("channel")
    target = params.get("target") if isinstance(params.get("target"), dict) else {}
    thread = params.get("thread") if isinstance(params.get("thread"), dict) else {}
    to = target.get("to") or params.get("to")
    if not channel and not to:
        return None
    result: dict[str, Any] = {}
    if channel:
        result["channel"] = channel
    if to:
        result["to"] = to
    if target.get("rawTo"):
        result["rawTo"] = target["rawTo"]
    if target.get("chatType"):
        result["chatType"] = target["chatType"]
    if params.get("accountId"):
        result["accountId"] = params["accountId"]
    if thread.get("id") is not None:
        result["threadId"] = thread["id"]
    if thread.get("kind"):
        result["threadKind"] = thread["kind"]
    if thread.get("source"):
        result["threadSource"] = thread["source"]
    return result or None


def _channel_route_target(route: dict | None) -> str | None:
    if not route:
        return None
    return route.get("to")


def _channel_route_thread_id(route: dict | None) -> str | int | None:
    if not route:
        return None
    return route.get("threadId")


def _channel_route_compact_key(route: dict | None) -> str | None:
    if not route:
        return None
    parts = [route.get("channel"), route.get("to"), route.get("accountId"), route.get("threadId")]
    filtered = [str(p) for p in parts if p is not None]
    return "|".join(filtered) if filtered else None


def normalize_delivery_context(context: DeliveryContext | None = None) -> DeliveryContext | None:
    if not context:
        return None
    route = _normalize_channel_route_target(
        {
            "channel": (
                normalize_message_channel(context.get("channel")) or (context.get("channel", "").strip())
                if isinstance(context.get("channel"), str)
                else None
            ),
            "to": context.get("to"),
            "accountId": context.get("accountId"),
            "threadId": context.get("threadId"),
        }
    )
    if not route:
        return None
    normalized: dict[str, Any] = {
        "channel": route.get("channel"),
        "to": _channel_route_target(route),
        "accountId": normalize_account_id(route.get("accountId")),
    }
    thread_id = _channel_route_thread_id(route)
    if thread_id is not None:
        normalized["threadId"] = thread_id
    return normalized


def normalize_delivery_channel_route(route: Any = None) -> dict | None:
    if not route or not isinstance(route, dict) or isinstance(route, list):
        return None
    target = route.get("target") if isinstance(route.get("target"), dict) else {}
    thread = route.get("thread") if isinstance(route.get("thread"), dict) else {}
    return _normalize_channel_route_ref(
        {
            "channel": route.get("channel"),
            "to": target.get("to"),
            "rawTo": target.get("rawTo"),
            "chatType": target.get("chatType"),
            "accountId": route.get("accountId"),
            "threadId": thread.get("id"),
            "threadKind": thread.get("kind"),
            "threadSource": thread.get("source"),
        }
    )


def delivery_context_from_channel_route(route: dict | None = None) -> DeliveryContext | None:
    normalized = normalize_delivery_channel_route(route)
    return normalize_delivery_context(
        {
            "channel": normalized.get("channel") if normalized else None,
            "to": _channel_route_target(normalized),
            "accountId": normalized.get("accountId") if normalized else None,
            "threadId": _channel_route_thread_id(normalized),
        }
    )


def channel_route_from_delivery_context(context: DeliveryContext | None = None) -> dict | None:
    return _normalize_channel_route_target(normalize_delivery_context(context))


def _merge_route_metadata_with_delivery_context(
    route: dict | None, context: DeliveryContext
) -> dict | None:
    if not route:
        return channel_route_from_delivery_context(context)
    target = route.get("target") if isinstance(route.get("target"), dict) else {}
    thread = route.get("thread") if isinstance(route.get("thread"), dict) else {}
    return _normalize_channel_route_ref(
        {
            "channel": route.get("channel") or context.get("channel"),
            "to": target.get("to") or context.get("to"),
            "rawTo": target.get("rawTo"),
            "chatType": target.get("chatType"),
            "accountId": route.get("accountId") or context.get("accountId"),
            "threadId": thread.get("id") or context.get("threadId"),
            "threadKind": thread.get("kind"),
            "threadSource": thread.get("source"),
        }
    )


def _is_internal_route_context(context: DeliveryContext | None) -> bool:
    channel = context.get("channel") if context else None
    return bool(channel and (channel == INTERNAL_MESSAGE_CHANNEL or is_internal_non_delivery_channel(channel)))


def _has_external_delivery_target(context: DeliveryContext | None) -> bool:
    channel = normalize_message_channel(context.get("channel") if context else None)
    return bool(
        channel
        and not is_internal_non_delivery_channel(channel)
        and is_deliverable_message_channel(channel)
        and context
        and context.get("to")
    )


def _merge_external_delivery_context_over_internal_route(
    delivery_context: DeliveryContext | None = None,
    internal_context: DeliveryContext | None = None,
) -> DeliveryContext | None:
    return normalize_delivery_context(
        {
            "channel": delivery_context.get("channel") if delivery_context else None,
            "to": delivery_context.get("to") if delivery_context else None,
            "accountId": (delivery_context.get("accountId") if delivery_context else None)
            or (internal_context.get("accountId") if internal_context else None),
            "threadId": (delivery_context.get("threadId") if delivery_context else None)
            or (internal_context.get("threadId") if internal_context else None),
        }
    )


def normalize_session_delivery_fields(source: DeliveryContextSessionSource | None = None) -> dict:
    empty = {
        "route": None,
        "deliveryContext": None,
        "lastChannel": None,
        "lastTo": None,
        "lastAccountId": None,
        "lastThreadId": None,
    }
    if not source:
        return empty

    normalized_route = normalize_delivery_channel_route(source.get("route"))
    route_context = delivery_context_from_channel_route(normalized_route)
    legacy_context = normalize_delivery_context(
        {
            "channel": source.get("lastChannel") or source.get("channel"),
            "to": source.get("lastTo"),
            "accountId": source.get("lastAccountId"),
            "threadId": source.get("lastThreadId"),
        }
    )
    delivery_context = normalize_delivery_context(source.get("deliveryContext"))
    session_context = (
        _merge_external_delivery_context_over_internal_route(delivery_context, legacy_context)
        if _is_internal_route_context(legacy_context) and _has_external_delivery_target(delivery_context)
        else merge_delivery_context(legacy_context, delivery_context)
    )
    route_internal_context = merge_delivery_context(route_context, legacy_context)
    route_is_internal_fallback = _is_internal_route_context(
        route_context
    ) and _has_external_delivery_target(delivery_context)
    merged = (
        _merge_external_delivery_context_over_internal_route(delivery_context, route_internal_context)
        if route_is_internal_fallback
        else merge_delivery_context(route_context, session_context)
    )

    if not merged:
        return empty

    return {
        "route": _merge_route_metadata_with_delivery_context(
            None if route_is_internal_fallback else normalized_route, merged
        ),
        "deliveryContext": merged,
        "lastChannel": merged.get("channel"),
        "lastTo": merged.get("to"),
        "lastAccountId": merged.get("accountId"),
        "lastThreadId": merged.get("threadId"),
    }


def delivery_context_from_session(entry: DeliveryContextSessionSource | None = None) -> DeliveryContext | None:
    if not entry:
        return None
    origin = entry.get("origin") if isinstance(entry.get("origin"), dict) else {}
    delivery_ctx = entry.get("deliveryContext") if isinstance(entry.get("deliveryContext"), dict) else {}
    source: dict[str, Any] = {
        "route": entry.get("route"),
        "channel": entry.get("channel") or origin.get("provider"),
        "lastChannel": entry.get("lastChannel"),
        "lastTo": entry.get("lastTo"),
        "lastAccountId": entry.get("lastAccountId") or origin.get("accountId"),
        "lastThreadId": entry.get("lastThreadId") or delivery_ctx.get("threadId") or origin.get("threadId"),
        "origin": origin,
        "deliveryContext": entry.get("deliveryContext"),
    }
    return normalize_session_delivery_fields(source).get("deliveryContext")


def merge_delivery_context(
    primary: DeliveryContext | None = None,
    fallback: DeliveryContext | None = None,
) -> DeliveryContext | None:
    normalized_primary = normalize_delivery_context(primary)
    normalized_fallback = normalize_delivery_context(fallback)
    if not normalized_primary and not normalized_fallback:
        return None
    channels_conflict = bool(
        normalized_primary
        and normalized_primary.get("channel")
        and normalized_fallback
        and normalized_fallback.get("channel")
        and normalized_primary["channel"] != normalized_fallback["channel"]
    )
    return normalize_delivery_context(
        {
            "channel": (normalized_primary or {}).get("channel") or (normalized_fallback or {}).get("channel"),
            "to": (normalized_primary or {}).get("to")
            if channels_conflict
            else ((normalized_primary or {}).get("to") or (normalized_fallback or {}).get("to")),
            "accountId": (normalized_primary or {}).get("accountId")
            if channels_conflict
            else ((normalized_primary or {}).get("accountId") or (normalized_fallback or {}).get("accountId")),
            "threadId": (normalized_primary or {}).get("threadId")
            if channels_conflict
            else ((normalized_primary or {}).get("threadId") or (normalized_fallback or {}).get("threadId")),
        }
    )


def delivery_context_key(context: DeliveryContext | None = None) -> str | None:
    return _channel_route_compact_key(normalize_delivery_context(context))
