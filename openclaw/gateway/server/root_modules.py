"""Gateway server root modules — close reason, hook client IP config, TLS, presence events."""

from .close_reason import truncate_close_reason, CLOSE_REASON_MAX_BYTES
from .hook_client_ip_config import resolve_hook_client_ip_config
from .tls import load_gateway_tls_runtime, GatewayTlsRuntime
from .presence_events import broadcast_presence_snapshot

__all__ = [
    "truncate_close_reason",
    "CLOSE_REASON_MAX_BYTES",
    "resolve_hook_client_ip_config",
    "load_gateway_tls_runtime",
    "GatewayTlsRuntime",
    "broadcast_presence_snapshot",
]
