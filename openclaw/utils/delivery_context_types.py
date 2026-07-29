from __future__ import annotations

from typing import Any, TypedDict


class DeliveryIntentRef(TypedDict, total=False):
    id: str
    kind: str
    queuePolicy: str


class DeliveryContext(TypedDict, total=False):
    channel: str
    to: str
    accountId: str
    threadId: str | int
    deliveryIntent: DeliveryIntentRef


class _Origin(TypedDict, total=False):
    provider: str
    accountId: str
    threadId: str | int


class DeliveryContextSessionSource(TypedDict, total=False):
    route: Any
    channel: str
    lastChannel: str
    lastTo: str
    lastAccountId: str
    lastThreadId: str | int
    origin: _Origin
    deliveryContext: DeliveryContext
