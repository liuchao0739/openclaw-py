"""Keep server maxPayload aligned with gateway client maxPayload so high-res canvas snapshots

Mirrors src/gateway/server-constants.ts.
"""

from __future__ import annotations

from typing import Any

MAX_PAYLOAD_BYTES: Any = None
MAX_BUFFERED_BYTES: Any = None
MAX_PREAUTH_PAYLOAD_BYTES: Any = None
get_max_chat_history_messages_bytes: Any = None
set_max_chat_history_messages_bytes_for_test: Any = None
TICK_INTERVAL_MS: Any = None
HEALTH_REFRESH_INTERVAL_MS: Any = None
DEDUPE_TTL_MS: Any = None
DEDUPE_MAX: Any = None

