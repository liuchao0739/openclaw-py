from __future__ import annotations

import threading
import time
from typing import Any, Callable
from urllib.parse import urlsplit

LOG_URL_MAX_CHARS = 500
URL_SECRET_SUFFIX_PATTERN = ("?", "#")


def _sanitize_timeout_log_url(raw_url: str | None) -> str | None:
    trimmed = (raw_url or "").strip()
    if not trimmed:
        return None
    try:
        parts = urlsplit(trimmed)
        scheme = parts.scheme or ""
        netloc = parts.hostname or ""
        if parts.port:
            netloc += f":{parts.port}"
        path = parts.path or ""
        value = f"{scheme}://{netloc}{path}" if scheme else path
        if len(value) > LOG_URL_MAX_CHARS:
            return f"{value[:LOG_URL_MAX_CHARS]}..."
        return value
    except Exception:
        for sep in URL_SECRET_SUFFIX_PATTERN:
            if sep in trimmed:
                trimmed = trimmed.split(sep, 1)[0]
        import re

        cleaned = re.sub(r"[\r\n\u2028\u2029]+", " ", trimmed)
        cleaned = re.sub(r"[\x00-\x1f\x7f]+", " ", cleaned)
        cleaned = re.sub(r"\s+", " ", cleaned).strip()
        if not cleaned:
            return None
        if len(cleaned) > LOG_URL_MAX_CHARS:
            return f"{cleaned[:LOG_URL_MAX_CHARS]}..."
        return cleaned


def _abort_due_to_timeout(
    controller: threading.Event,
    timeout_ms: int,
    started_at_ms: float,
    operation: str | None = None,
    url: str | None = None,
) -> None:
    if controller.is_set():
        return
    sanitized_url = _sanitize_timeout_log_url(url)
    elapsed_ms = max(0, time.time() * 1000 - started_at_ms)
    delay_ms = max(0, elapsed_ms - timeout_ms)
    event_loop_delay_hint = None
    if delay_ms >= max(1000, timeout_ms * 0.5):
        event_loop_delay_hint = f"timer delayed {delay_ms}ms, likely event-loop starvation"
    parts = [
        f"fetch timeout after {timeout_ms}ms",
        f"(elapsed {elapsed_ms}ms)",
        event_loop_delay_hint,
        f"operation={operation}" if operation else None,
        f"url={sanitized_url}" if sanitized_url else None,
    ]
    console_message = " ".join(p for p in parts if p)
    controller.set()


def build_timeout_abort_signal(params: dict) -> dict:
    timeout_ms = params.get("timeoutMs")
    signal = params.get("signal")
    if not timeout_ms and not signal:
        return {"signal": None, "cleanup": lambda: None, "refresh": lambda: None}
    if not timeout_ms:
        return {"signal": signal, "cleanup": lambda: None, "refresh": lambda: None}

    controller = threading.Event()
    from openclaw.utils.timer_delay import resolve_safe_timeout_delay_ms

    normalized_timeout_ms = resolve_safe_timeout_delay_ms(timeout_ms)
    state: dict[str, Any] = {"active": True, "timer": None}

    def _schedule_timeout() -> None:
        timer = threading.Timer(
            normalized_timeout_ms / 1000.0,
            _abort_due_to_timeout,
            args=(controller, normalized_timeout_ms, time.time() * 1000, params.get("operation"), params.get("url")),
        )
        timer.daemon = True
        state["timer"] = timer
        timer.start()

    _schedule_timeout()

    def _refresh() -> None:
        if not state["active"] or controller.is_set():
            return
        if state["timer"]:
            state["timer"].cancel()
        _schedule_timeout()

    def _cleanup() -> None:
        state["active"] = False
        if state["timer"]:
            state["timer"].cancel()

    return {"signal": controller, "cleanup": _cleanup, "refresh": _refresh}


def fetch_with_timeout(url: str, init: dict, timeout_ms: int, fetch_fn: Callable | None = None) -> Any:
    import requests

    fn = fetch_fn or requests.request
    built = build_timeout_abort_signal(
        {"timeoutMs": max(1, timeout_ms), "operation": "fetchWithTimeout", "url": url}
    )
    try:
        method = init.get("method", "GET")
        headers = init.get("headers")
        body = init.get("body")
        return fn(method, url, headers=headers, data=body, timeout=timeout_ms / 1000.0)
    finally:
        built["cleanup"]()
