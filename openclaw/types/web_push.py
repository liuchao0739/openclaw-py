from typing import Any, Awaitable, Callable, Dict, Optional


class PushSubscription:
    endpoint: str
    keys: "_PushSubscriptionKeys"


class _PushSubscriptionKeys:
    p256dh: str
    auth: str


class SendResult:
    status_code: int
    body: str
    headers: Dict[str, str]


class VAPIDKeys:
    public_key: str
    private_key: str


def generateVAPIDKeys() -> VAPIDKeys:
    ...


def setVapidDetails(subject: str, public_key: str, private_key: str) -> None:
    ...


def sendNotification(
    subscription: PushSubscription,
    payload: Optional[str] = None,
    options: Optional[Dict[str, Any]] = None,
) -> Awaitable[SendResult]:
    ...
