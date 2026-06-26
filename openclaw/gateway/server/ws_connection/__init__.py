"""WebSocket connection package — flood guard and auth messages."""

from .unauthorized_flood_guard import (
    UnauthorizedFloodGuard,
    is_unauthorized_role_error,
)
from .auth_messages import (
    AuthProvidedKind,
    format_gateway_auth_failure_message,
)

__all__ = [
    "UnauthorizedFloodGuard",
    "is_unauthorized_role_error",
    "AuthProvidedKind",
    "format_gateway_auth_failure_message",
]
