"""In-memory sliding-window rate limiter for gateway authentication attempts.

Mirrors src/gateway/auth-rate-limit.ts.
"""

from __future__ import annotations

from typing import Any

AUTH_RATE_LIMIT_SCOPE_DEFAULT: Any = None
AUTH_RATE_LIMIT_SCOPE_SHARED_SECRET: Any = None
AUTH_RATE_LIMIT_SCOPE_DEVICE_TOKEN: Any = None
AUTH_RATE_LIMIT_SCOPE_NODE_PAIRING: Any = None
AUTH_RATE_LIMIT_SCOPE_NODE_REAPPROVAL: Any = None
AUTH_RATE_LIMIT_SCOPE_BOOTSTRAP_TOKEN: Any = None
AUTH_RATE_LIMIT_SCOPE_HOOK_AUTH: Any = None

class RateLimitConfig: ...
class RateLimitCheckResult: ...
class AuthRateLimiter: ...

def normalize_rate_limit_client_ip(*args: Any, **kwargs: Any) -> Any: ...
def build_rate_limit_identity_key(*args: Any, **kwargs: Any) -> Any: ...
def create_auth_rate_limiter(*args: Any, **kwargs: Any) -> Any: ...
