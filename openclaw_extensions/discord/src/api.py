import asyncio
import json
import re
from typing import Any, Dict, Optional


DISCORD_API_BASE = "https://discord.com/api/v10"
DISCORD_API_RETRY_DEFAULTS = {
    "attempts": 3,
    "minDelayMs": 500,
    "maxDelayMs": 5 * 60_000,
    "jitter": 0.1,
}
DISCORD_API_429_FALLBACK_RETRY_AFTER_SECONDS = 60
DISCORD_API_ERROR_BODY_LIMIT_BYTES = 8 * 1024


class DiscordApiError(Exception):
    def __init__(self, message: str, status: int, retry_after: Optional[float] = None):
        super().__init__(message)
        self.status = status
        self.retry_after = retry_after


def parse_discord_api_error_payload(text: str) -> Optional[Dict[str, Any]]:
    trimmed = text.strip()
    if not trimmed.startswith("{") or not trimmed.endswith("}"):
        return None
    try:
        payload = json.loads(trimmed)
        if isinstance(payload, dict):
            return payload
    except Exception:
        return None
    return None


def parse_retry_after_header_seconds(header: str) -> Optional[float]:
    try:
        value = float(header)
        if value >= 0:
            return value
    except (TypeError, ValueError):
        pass
    return None


def parse_discord_retry_after_body_seconds(value: Any) -> Optional[float]:
    if value is None:
        return None
    try:
        parsed = float(value)
        if parsed >= 0:
            return parsed
    except (TypeError, ValueError):
        return None
    return None


def parse_retry_after_seconds(text: str, response: Any) -> Optional[float]:
    payload = parse_discord_api_error_payload(text)
    retry_after = parse_discord_retry_after_body_seconds(payload.get("retry_after") if payload else None)
    if retry_after is not None:
        return retry_after
    headers = getattr(response, "headers", {}) or {}
    header = headers.get("Retry-After") or headers.get("retry-after")
    if not header:
        return None
    return parse_retry_after_header_seconds(header)


def format_retry_after_seconds(value: Optional[float]) -> Optional[str]:
    if value is None or not isinstance(value, (int, float)) or value < 0:
        return None
    rounded = f"{value:.1f}" if value < 10 else str(round(value))
    return f"{rounded}s"


def summarize_discord_response_body(text: str) -> Optional[str]:
    trimmed = text.strip()
    if not trimmed:
        return None
    if len(trimmed) > 200:
        return trimmed[:200] + "..."
    return trimmed


def is_discord_html_response_body(text: str, content_type: Optional[str]) -> bool:
    if content_type and "text/html" in content_type.lower():
        return True
    return trimmed_starts_with_html(text)


def trimmed_starts_with_html(text: str) -> bool:
    return text.strip().lower().startswith(("<!doctype", "<html"))


def format_discord_api_error_text(text: str, response: Any) -> Optional[str]:
    trimmed = text.strip()
    if not trimmed:
        return None
    payload = parse_discord_api_error_payload(trimmed)
    if not payload:
        looks_json = trimmed.startswith("{") and trimmed.endswith("}")
        if looks_json:
            return "unknown error"
        summary = summarize_discord_response_body(trimmed)
        headers = getattr(response, "headers", {}) or {}
        content_type = headers.get("Content-Type") or headers.get("content-type")
        if is_discord_html_response_body(trimmed, content_type):
            status = getattr(response, "status", None)
            if not summary:
                return "rate limited by Discord upstream" if status == 429 else None
            return (
                f"rate limited by Discord upstream: {summary}"
                if status == 429
                else summary
            )
        return summary
    message = (
        payload.get("message", "").strip()
        if isinstance(payload.get("message"), str) and payload.get("message", "").strip()
        else "unknown error"
    )
    retry_after = format_retry_after_seconds(
        parse_discord_retry_after_body_seconds(payload.get("retry_after"))
    )
    return f"{message} (retry after {retry_after})" if retry_after else message


def get_discord_api_retry_after_ms(err: Exception, retry_config: Dict[str, Any]) -> Optional[int]:
    if not isinstance(err, DiscordApiError) or err.retry_after is None:
        return None
    return min(max(0, int(err.retry_after * 1000)), retry_config["maxDelayMs"])


def normalize_discord_request_body(body: Any, headers: Dict[str, str]) -> Any:
    if body is None:
        return None
    if isinstance(body, (str, bytes, bytearray)):
        return body
    headers.setdefault("Content-Type", "application/json")
    return json.dumps(body)


async def retry_async(func, retry_config: Dict[str, Any]):
    attempts = retry_config.get("attempts", 3)
    min_delay = retry_config.get("minDelayMs", 500) / 1000
    max_delay = retry_config.get("maxDelayMs", 60_000) / 1000
    jitter = retry_config.get("jitter", 0.1)
    should_retry = retry_config.get("shouldRetry")
    retry_after_ms = retry_config.get("retryAfterMs")
    last_error: Optional[Exception] = None
    for attempt in range(attempts):
        try:
            return await func()
        except Exception as err:
            last_error = err
            if should_retry and not should_retry(err):
                raise
            if attempt + 1 >= attempts:
                raise
            delay = min_delay * (2 ** attempt)
            if retry_after_ms:
                custom = retry_after_ms(err)
                if custom is not None:
                    delay = custom / 1000
            delay = min(delay, max_delay)
            await asyncio.sleep(delay)
    if last_error:
        raise last_error


async def request_discord(path: str, token: str, options: Optional[Dict[str, Any]] = None) -> Any:
    options = options or {}
    headers = dict(options.get("headers") or {})
    headers["Authorization"] = f"Bot {token}"
    body = normalize_discord_request_body(options.get("body"), headers)
    method = options.get("method") or ("POST" if body is not None else "GET")

    retry_config = dict(DISCORD_API_RETRY_DEFAULTS)
    retry_config.update(options.get("retry") or {})
    retry_config["label"] = options.get("label", path)
    retry_config["shouldRetry"] = lambda err: isinstance(err, DiscordApiError) and err.status == 429
    retry_config["retryAfterMs"] = lambda err: get_discord_api_retry_after_ms(err, retry_config)

    async def call():
        try:
            import aiohttp

            async with aiohttp.ClientSession() as session:
                async with session.request(
                    method,
                    f"{DISCORD_API_BASE}{path}",
                    headers=headers,
                    data=body,
                ) as response:
                    if response.status >= 400:
                        text = await response.text()
                        detail = format_discord_api_error_text(text, response)
                        suffix = f": {detail}" if detail else ""
                        retry_after = (
                            parse_retry_after_seconds(text, response)
                            if response.status == 429
                            else None
                        )
                        if retry_after is None and response.status == 429:
                            retry_after = DISCORD_API_429_FALLBACK_RETRY_AFTER_SECONDS
                        raise DiscordApiError(
                            f"Discord API {path} failed ({response.status}){suffix}",
                            response.status,
                            retry_after,
                        )
                    text = await response.text()
                    if not text.strip():
                        return None
                    return json.loads(text)
        except aiohttp_import_error():
            raise RuntimeError("aiohttp is not available")

    return await retry_async(call, retry_config)


def aiohttp_import_error():
    try:
        import aiohttp
        return None
    except ImportError:
        return ImportError("aiohttp is not available")


async def fetch_discord(path: str, token: str, options: Optional[Dict[str, Any]] = None) -> Any:
    merged = dict(options or {})
    merged["method"] = "GET"
    return await request_discord(path, token, merged)
