from __future__ import annotations

import os
import re
from typing import Final, Optional

MAX_SAFE_TIMEOUT_DELAY_MS: Final[int] = 2_147_483_647
DEFAULT_PREAUTH_HANDSHAKE_TIMEOUT_MS: Final[int] = 15_000
MIN_CONNECT_CHALLENGE_TIMEOUT_MS: Final[int] = 250
MAX_CONNECT_CHALLENGE_TIMEOUT_MS: Final[int] = DEFAULT_PREAUTH_HANDSHAKE_TIMEOUT_MS

_POSITIVE_INTEGER_RE = re.compile(r"^\+?\d+$")


def _parse_strict_positive_integer(value: str) -> Optional[int]:
    trimmed = value.strip()
    if not _POSITIVE_INTEGER_RE.fullmatch(trimmed):
        return None
    parsed = int(trimmed)
    if parsed > 0:
        return parsed
    return None


def resolve_safe_timeout_delay_ms(delay_ms: float, *, min_ms: int = 1) -> int:
    raw_min_ms = min(MAX_SAFE_TIMEOUT_DELAY_MS, max(0, int(min_ms) if min_ms == int(min_ms) else 1))
    if not (MAX_SAFE_TIMEOUT_DELAY_MS >= raw_min_ms >= 0):
        raw_min_ms = 1
    candidate = int(delay_ms) if delay_ms == int(delay_ms) and delay_ms == delay_ms else raw_min_ms
    return min(MAX_SAFE_TIMEOUT_DELAY_MS, max(raw_min_ms, candidate))


def add_safe_timeout_delay_grace_ms(
    delay_ms: float,
    grace_ms: float,
    *,
    min_ms: int = 1,
) -> int:
    if not (delay_ms == delay_ms) or not (grace_ms == grace_ms):
        return resolve_safe_timeout_delay_ms(MAX_SAFE_TIMEOUT_DELAY_MS, min_ms=min_ms)
    with_grace = delay_ms + grace_ms
    safe_value = with_grace if with_grace == with_grace else MAX_SAFE_TIMEOUT_DELAY_MS
    return resolve_safe_timeout_delay_ms(int(safe_value), min_ms=min_ms)


def resolve_finite_timeout_delay_ms(
    delay_ms: Optional[float],
    fallback_ms: float,
    *,
    min_ms: int = 1,
) -> int:
    candidate = delay_ms if (delay_ms is not None and delay_ms == int(delay_ms) and delay_ms == delay_ms) else fallback_ms
    return resolve_safe_timeout_delay_ms(int(candidate), min_ms=min_ms)


def clamp_connect_challenge_timeout_ms(
    timeout_ms: float,
    max_timeout_ms: int = MAX_CONNECT_CHALLENGE_TIMEOUT_MS,
) -> int:
    return max(
        MIN_CONNECT_CHALLENGE_TIMEOUT_MS,
        min(max(MIN_CONNECT_CHALLENGE_TIMEOUT_MS, max_timeout_ms), int(timeout_ms)),
    )


def get_connect_challenge_timeout_ms_from_env(
    env: Optional[dict] = None,
) -> Optional[int]:
    if env is None:
        env = os.environ
    raw = env.get("OPENCLAW_CONNECT_CHALLENGE_TIMEOUT_MS")
    if raw:
        parsed = _parse_strict_positive_integer(raw)
        if parsed is not None:
            return resolve_safe_timeout_delay_ms(parsed)
    return None


def _normalize_positive_timeout_ms(timeout_ms: object) -> Optional[int]:
    if isinstance(timeout_ms, (int, float)) and timeout_ms == timeout_ms and timeout_ms > 0:
        return resolve_safe_timeout_delay_ms(int(timeout_ms))
    return None


def resolve_connect_challenge_timeout_ms(
    timeout_ms: Optional[float] = None,
    params: Optional[dict] = None,
) -> int:
    if params is None:
        params = {}
    env = params.get("env")
    configured_timeout_ms = params.get("configuredTimeoutMs")

    configured_preauth = resolve_preauth_handshake_timeout_ms(
        env=env,
        configured_timeout_ms=configured_timeout_ms,
    )
    max_timeout_ms = max(DEFAULT_PREAUTH_HANDSHAKE_TIMEOUT_MS, configured_preauth)

    if isinstance(timeout_ms, (int, float)) and timeout_ms == timeout_ms:
        return clamp_connect_challenge_timeout_ms(int(timeout_ms), max_timeout_ms)

    env_override = get_connect_challenge_timeout_ms_from_env(env)
    if env_override is not None:
        return clamp_connect_challenge_timeout_ms(env_override, max(max_timeout_ms, env_override))

    return clamp_connect_challenge_timeout_ms(configured_preauth, max_timeout_ms)


def get_preauth_handshake_timeout_ms_from_env(
    env: Optional[dict] = None,
) -> int:
    if env is None:
        env = os.environ
    configured = env.get("OPENCLAW_HANDSHAKE_TIMEOUT_MS")
    if not configured and env.get("VITEST") and env.get("OPENCLAW_TEST_HANDSHAKE_TIMEOUT_MS"):
        configured = env.get("OPENCLAW_TEST_HANDSHAKE_TIMEOUT_MS")
    if configured:
        parsed = _parse_strict_positive_integer(configured)
        if parsed is not None:
            return resolve_safe_timeout_delay_ms(parsed)
    return DEFAULT_PREAUTH_HANDSHAKE_TIMEOUT_MS


def resolve_preauth_handshake_timeout_ms(
    params: Optional[dict] = None,
) -> int:
    if params is None:
        params = {}
    env = params.get("env")
    configured_timeout_ms = params.get("configuredTimeoutMs")

    if env is None:
        env = os.environ

    configured = env.get("OPENCLAW_HANDSHAKE_TIMEOUT_MS")
    if not configured and env.get("VITEST") and env.get("OPENCLAW_TEST_HANDSHAKE_TIMEOUT_MS"):
        configured = env.get("OPENCLAW_TEST_HANDSHAKE_TIMEOUT_MS")
    if configured:
        parsed = _parse_strict_positive_integer(configured)
        if parsed is not None:
            return resolve_safe_timeout_delay_ms(parsed)

    normalized = _normalize_positive_timeout_ms(configured_timeout_ms)
    if normalized is not None:
        return normalized

    return DEFAULT_PREAUTH_HANDSHAKE_TIMEOUT_MS
