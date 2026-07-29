import json
import time
import urllib.parse
from typing import Any, Callable, Optional

from .._sdk import (
    SsrfBlockedError,
    is_blocked_hostname_or_ip,
    is_private_ip_address,
    markdown_to_text,
    normalize_cache_key,
    normalize_secret_input,
    read_cache,
    read_provider_json_response,
    read_response_text,
    resolve_cache_ttl_ms,
    truncate_text,
    wrap_external_content,
    wrap_web_content,
    write_cache,
)
from .._sdk import with_self_hosted_web_tools_endpoint, with_strict_web_tools_endpoint
from .config import (
    DEFAULT_FIRECRAWL_BASE_URL,
    resolve_firecrawl_api_key,
    resolve_firecrawl_base_url,
    resolve_firecrawl_max_age_ms,
    resolve_firecrawl_only_main_content,
    resolve_firecrawl_scrape_timeout_seconds,
    resolve_firecrawl_search_timeout_seconds,
)

DEFAULT_CACHE_TTL_MINUTES = 15

SEARCH_CACHE: dict = {}
SCRAPE_CACHE: dict = {}
DEFAULT_SEARCH_COUNT = 5
DEFAULT_SCRAPE_MAX_CHARS = 50000
FIRECRAWL_SCRAPE_RESPONSE_MAX_BYTES = 64 * 1024 * 1024
ALLOWED_FIRECRAWL_HOSTS = {"api.firecrawl.dev"}
FIRECRAWL_SELF_HOSTED_PRIVATE_ERROR = "Firecrawl custom baseUrl must target a private or internal self-hosted endpoint."
FIRECRAWL_HTTP_PRIVATE_ERROR = "Firecrawl HTTP baseUrl must target a private or internal self-hosted endpoint. Use https:// for public hosts."


class FirecrawlSearchParams:
    def __init__(self, *, cfg: Optional[dict] = None, query: str, count: Optional[int] = None,
                 timeout_seconds: Optional[int] = None, sources: Optional[list] = None,
                 categories: Optional[list] = None, scrape_results: bool = False):
        self.cfg = cfg
        self.query = query
        self.count = count
        self.timeout_seconds = timeout_seconds
        self.sources = sources
        self.categories = categories
        self.scrape_results = scrape_results


class FirecrawlScrapeParams:
    def __init__(self, *, cfg: Optional[dict] = None, url: str, extract_mode: str,
                 access: Optional[str] = None, max_chars: Optional[int] = None,
                 only_main_content: Optional[bool] = None, max_age_ms: Optional[int] = None,
                 proxy: Optional[str] = None, store_in_cache: Optional[bool] = None,
                 timeout_seconds: Optional[int] = None):
        self.cfg = cfg
        self.url = url
        self.extract_mode = extract_mode
        self.access = access
        self.max_chars = max_chars
        self.only_main_content = only_main_content
        self.max_age_ms = max_age_ms
        self.proxy = proxy
        self.store_in_cache = store_in_cache
        self.timeout_seconds = timeout_seconds


def assert_firecrawl_scrape_target_allowed(url: str) -> None:
    try:
        parsed = urllib.parse.urlparse(url)
    except Exception:
        raise SsrfBlockedError("Invalid URL supplied to Firecrawl scrape")
    if parsed.scheme not in ("http", "https"):
        raise SsrfBlockedError(f"Blocked non-HTTP(S) protocol in Firecrawl scrape URL: {parsed.scheme}")
    hostname = parsed.hostname or ""
    if is_blocked_hostname_or_ip(hostname):
        raise SsrfBlockedError(f"Blocked hostname or private/internal IP in Firecrawl scrape URL: {hostname}")


def _is_official_firecrawl_endpoint(parsed_url: urllib.parse.ParseResult) -> bool:
    return parsed_url.scheme == "https" and parsed_url.hostname in ALLOWED_FIRECRAWL_HOSTS


def _firecrawl_endpoint_targets_private_network(parsed_url: urllib.parse.ParseResult) -> bool:
    hostname = parsed_url.hostname or ""
    if is_blocked_hostname_or_ip(hostname):
        return True
    return False


def _validate_firecrawl_base_url(base_url: str) -> str:
    try:
        parsed = urllib.parse.urlparse(base_url.strip() or DEFAULT_FIRECRAWL_BASE_URL)
    except Exception:
        raise RuntimeError("Firecrawl baseUrl must be a valid http:// or https:// URL.")
    if parsed.scheme not in ("http", "https"):
        raise RuntimeError("Firecrawl baseUrl must use http:// or https://.")
    if _is_official_firecrawl_endpoint(parsed):
        return "strict"
    is_private_target = _firecrawl_endpoint_targets_private_network(parsed)
    if is_private_target:
        return "selfHosted"
    if parsed.scheme == "http":
        raise RuntimeError(FIRECRAWL_HTTP_PRIVATE_ERROR)
    raise RuntimeError(f"{FIRECRAWL_SELF_HOSTED_PRIVATE_ERROR} Host: {parsed.hostname}")


def _resolve_endpoint(base_url: str, pathname: str) -> dict:
    parsed = urllib.parse.urlparse(base_url.strip() or DEFAULT_FIRECRAWL_BASE_URL)
    mode = _validate_firecrawl_base_url(parsed.geturl())
    netloc = parsed.hostname or ""
    if parsed.port:
        netloc = f"{parsed.hostname}:{parsed.port}"
    scheme = parsed.scheme
    new_parsed = urllib.parse.ParseResult(scheme=scheme, netloc=netloc, path=pathname, params="", query="", fragment="")
    return {"url": urllib.parse.urlunparse(new_parsed), "mode": mode}


def _post_firecrawl_json(*, url: str, mode: Optional[str], timeout_seconds: int,
                         api_key: Optional[str], body: dict, error_label: str,
                         parse: Callable) -> Any:
    key = normalize_secret_input(api_key)
    resolved_mode = mode or _validate_firecrawl_base_url(url)
    endpoint_fn = with_self_hosted_web_tools_endpoint if resolved_mode == "selfHosted" else with_strict_web_tools_endpoint
    headers = {"Content-Type": "application/json"}
    if key:
        headers["Authorization"] = f"Bearer {key}"

    def handler(ctx):
        response = ctx["response"]
        status = getattr(response, "status", None) or getattr(response, "code", None)
        if status is None or not (200 <= status < 300):
            detail = ""
            status_text = getattr(response, "status_text", "") or ""
            if status_text and status_text.strip():
                detail = status_text.strip()
            else:
                detail = "request failed"
            try:
                cloned_text = read_response_text(response, max_bytes=64000)
                payload = json.loads(cloned_text["text"])
                if isinstance(payload, dict):
                    detail = payload.get("error") or payload.get("message") or detail
            except Exception:
                error_body = read_response_text(response, max_bytes=64000)
                if error_body["text"]:
                    detail = error_body["text"]
            safe_detail = wrap_web_content(detail[:1000], "web_fetch")
            raise RuntimeError(f"{error_label} API error ({status}): {safe_detail}")
        return parse(response)

    return endpoint_fn(
        {
            "url": url,
            "timeoutSeconds": timeout_seconds,
            "init": {
                "method": "POST",
                "headers": headers,
                "body": json.dumps(body),
            },
        },
        handler,
    )


def _resolve_site_name(url_raw: str) -> Optional[str]:
    try:
        parsed = urllib.parse.urlparse(url_raw)
        host = (parsed.hostname or "").removeprefix("www.")
        return host or None
    except Exception:
        return None


def resolve_search_items(payload: dict) -> list:
    candidates = [
        payload.get("data"),
        payload.get("results"),
        payload.get("data", {}).get("results") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("data") if isinstance(payload.get("data"), dict) else None,
        payload.get("data", {}).get("web") if isinstance(payload.get("data"), dict) else None,
        payload.get("web", {}).get("results") if isinstance(payload.get("web"), dict) else None,
    ]
    raw_items = next((c for c in candidates if isinstance(c, list)), None)
    if not raw_items:
        return []
    items = []
    for entry in raw_items:
        if not isinstance(entry, dict):
            continue
        metadata = entry.get("metadata") if isinstance(entry.get("metadata"), dict) else None
        url = ""
        if isinstance(entry.get("url"), str) and entry["url"]:
            url = entry["url"]
        elif isinstance(entry.get("sourceURL"), str) and entry["sourceURL"]:
            url = entry["sourceURL"]
        elif isinstance(entry.get("sourceUrl"), str) and entry["sourceUrl"]:
            url = entry["sourceUrl"]
        elif metadata and isinstance(metadata.get("sourceURL"), str) and metadata["sourceURL"]:
            url = metadata["sourceURL"]
        if not url:
            continue
        title = ""
        if isinstance(entry.get("title"), str) and entry["title"]:
            title = entry["title"]
        elif metadata and isinstance(metadata.get("title"), str) and metadata["title"]:
            title = metadata["title"]
        description = None
        for key in ("description", "snippet", "summary"):
            if isinstance(entry.get(key), str) and entry[key]:
                description = entry[key]
                break
        content = None
        for key in ("markdown", "content", "text"):
            if isinstance(entry.get(key), str) and entry[key]:
                content = entry[key]
                break
        published = None
        if isinstance(entry.get("publishedDate"), str) and entry["publishedDate"]:
            published = entry["publishedDate"]
        elif isinstance(entry.get("published"), str) and entry["published"]:
            published = entry["published"]
        elif metadata:
            for key in ("publishedTime", "publishedDate"):
                if isinstance(metadata.get(key), str) and metadata[key]:
                    published = metadata[key]
                    break
        items.append({
            "title": title,
            "url": url,
            "description": description,
            "content": content,
            "published": published,
            "siteName": _resolve_site_name(url),
        })
    return items


def _build_search_payload(*, query: str, provider: str, items: list, took_ms: int, scrape_results: bool) -> dict:
    results = []
    for entry in items:
        item = {
            "title": wrap_web_content(entry["title"], "web_search") if entry["title"] else "",
            "url": entry["url"],
            "description": wrap_web_content(entry["description"], "web_search") if entry["description"] else "",
        }
        if entry.get("published"):
            item["published"] = entry["published"]
        if entry.get("siteName"):
            item["siteName"] = entry["siteName"]
        if scrape_results and entry.get("content"):
            item["content"] = wrap_web_content(entry["content"], "web_search")
        results.append(item)
    return {
        "query": query,
        "provider": provider,
        "count": len(items),
        "tookMs": took_ms,
        "externalContent": {
            "untrusted": True,
            "source": "web_search",
            "provider": provider,
            "wrapped": True,
        },
        "results": results,
    }


def run_firecrawl_search(params: FirecrawlSearchParams) -> dict:
    api_key = resolve_firecrawl_api_key(params.cfg)
    if not api_key:
        raise RuntimeError(
            "web_search (firecrawl) needs a Firecrawl API key. Set FIRECRAWL_API_KEY in the Gateway environment, or configure plugins.entries.firecrawl.config.webSearch.apiKey."
        )
    if isinstance(params.count, (int, float)) and params.count == params.count:
        count = max(1, min(10, int(params.count)))
    else:
        count = DEFAULT_SEARCH_COUNT
    timeout_seconds = resolve_firecrawl_search_timeout_seconds(params.timeout_seconds)
    scrape_results = params.scrape_results is True
    sources = [s for s in (params.sources or []) if s]
    categories = [c for c in (params.categories or []) if c]
    base_url = resolve_firecrawl_base_url(params.cfg)
    cache_key = normalize_cache_key(json.dumps({
        "type": "firecrawl-search",
        "q": params.query,
        "count": count,
        "baseUrl": base_url,
        "sources": sources,
        "categories": categories,
        "scrapeResults": scrape_results,
    }))
    cached = read_cache(SEARCH_CACHE, cache_key)
    if cached:
        return {**cached["value"], "cached": True}

    body: dict = {"query": params.query, "limit": count}
    if sources:
        body["sources"] = sources
    if categories:
        body["categories"] = categories
    if scrape_results:
        body["scrapeOptions"] = {"formats": ["markdown"]}

    start = int(time.time() * 1000)
    endpoint = _resolve_endpoint(base_url, "/v2/search")

    def parse(response):
        payload_value = read_provider_json_response(response, "Firecrawl Search API error")
        if payload_value.get("success") is False:
            error = payload_value.get("error") or payload_value.get("message") or "unknown error"
            raise RuntimeError(f"Firecrawl Search API error: {error}")
        return payload_value

    payload = _post_firecrawl_json(
        url=endpoint["url"],
        mode=endpoint["mode"],
        timeout_seconds=timeout_seconds,
        api_key=api_key,
        body=body,
        error_label="Firecrawl Search",
        parse=parse,
    )
    result = _build_search_payload(
        query=params.query,
        provider="firecrawl",
        items=resolve_search_items(payload),
        took_ms=int(time.time() * 1000) - start,
        scrape_results=scrape_results,
    )
    write_cache(SEARCH_CACHE, cache_key, result, resolve_cache_ttl_ms(None, DEFAULT_CACHE_TTL_MINUTES))
    return result


def _resolve_scrape_data(payload: dict) -> dict:
    data = payload.get("data")
    if isinstance(data, dict):
        return data
    return {}


def parse_firecrawl_scrape_payload(*, payload: dict, url: str, extract_mode: str, max_chars: int) -> dict:
    data = _resolve_scrape_data(payload)
    metadata = data.get("metadata") if isinstance(data.get("metadata"), dict) else None
    markdown = ""
    if isinstance(data.get("markdown"), str) and data["markdown"]:
        markdown = data["markdown"]
    elif isinstance(data.get("content"), str) and data["content"]:
        markdown = data["content"]
    if not markdown:
        raise RuntimeError("Firecrawl scrape returned no content.")
    raw_text = markdown_to_text(markdown) if extract_mode == "text" else markdown
    truncated = truncate_text(raw_text, max_chars)
    final_url = url
    if metadata and isinstance(metadata.get("sourceURL"), str) and metadata["sourceURL"]:
        final_url = metadata["sourceURL"]
    elif isinstance(data.get("url"), str) and data["url"]:
        final_url = data["url"]
    status = None
    if metadata and isinstance(metadata.get("statusCode"), int):
        status = metadata["statusCode"]
    elif isinstance(data.get("statusCode"), int):
        status = data["statusCode"]
    title = None
    if metadata and isinstance(metadata.get("title"), str) and metadata["title"]:
        title = wrap_external_content(metadata["title"], source="web_fetch", include_warning=False)
    wrapped_text = wrap_external_content(truncated["text"], source="web_fetch", include_warning=False)
    warning = None
    if isinstance(payload.get("warning"), str) and payload["warning"]:
        warning = wrap_external_content(payload["warning"], source="web_fetch", include_warning=False)
    return {
        "url": url,
        "finalUrl": final_url,
        "status": status,
        "title": title,
        "extractor": "firecrawl",
        "extractMode": extract_mode,
        "externalContent": {"untrusted": True, "source": "web_fetch", "wrapped": True},
        "truncated": truncated["truncated"],
        "rawLength": len(raw_text),
        "wrappedLength": len(wrapped_text),
        "text": wrapped_text,
        "warning": warning,
    }


def run_firecrawl_scrape(params: FirecrawlScrapeParams) -> dict:
    assert_firecrawl_scrape_target_allowed(params.url)

    api_key = resolve_firecrawl_api_key(params.cfg)
    if not api_key and params.access != "keyless":
        raise RuntimeError(
            "firecrawl_scrape needs a Firecrawl API key. Set FIRECRAWL_API_KEY in the Gateway environment, or configure plugins.entries.firecrawl.config.webFetch.apiKey."
        )
    base_url = resolve_firecrawl_base_url(params.cfg)
    timeout_seconds = resolve_firecrawl_scrape_timeout_seconds(params.cfg, params.timeout_seconds)
    only_main_content = resolve_firecrawl_only_main_content(params.cfg, params.only_main_content)
    max_age_ms = resolve_firecrawl_max_age_ms(params.cfg, params.max_age_ms)
    proxy = params.proxy or "auto"
    store_in_cache = True if params.store_in_cache is None else params.store_in_cache
    if isinstance(params.max_chars, (int, float)) and params.max_chars == params.max_chars and params.max_chars > 0:
        max_chars = int(params.max_chars)
    else:
        max_chars = DEFAULT_SCRAPE_MAX_CHARS
    cache_key = normalize_cache_key(json.dumps({
        "type": "firecrawl-scrape",
        "url": params.url,
        "extractMode": params.extract_mode,
        "baseUrl": base_url,
        "onlyMainContent": only_main_content,
        "maxAgeMs": max_age_ms,
        "proxy": proxy,
        "storeInCache": store_in_cache,
        "maxChars": max_chars,
    }))
    cached = read_cache(SCRAPE_CACHE, cache_key)
    if cached:
        return {**cached["value"], "cached": True}

    endpoint = _resolve_endpoint(base_url, "/v2/scrape")

    def parse(response):
        payload_local = read_provider_json_response(
            response, "Firecrawl fetch failed", max_bytes=FIRECRAWL_SCRAPE_RESPONSE_MAX_BYTES
        )
        if payload_local.get("success") is False:
            detail = payload_local.get("error") or payload_local.get("message") or getattr(response, "status_text", "")
            raise RuntimeError(f"Firecrawl fetch failed ({response.status}): {wrap_web_content(detail, 'web_fetch')}".strip())
        return payload_local

    payload = _post_firecrawl_json(
        url=endpoint["url"],
        mode=endpoint["mode"],
        timeout_seconds=timeout_seconds,
        api_key=api_key,
        error_label="Firecrawl",
        body={
            "url": params.url,
            "formats": ["markdown"],
            "onlyMainContent": only_main_content,
            "timeout": timeout_seconds * 1000,
            "maxAge": max_age_ms,
            "proxy": proxy,
            "storeInCache": store_in_cache,
        },
        parse=parse,
    )
    result = parse_firecrawl_scrape_payload(
        payload=payload,
        url=params.url,
        extract_mode=params.extract_mode,
        max_chars=max_chars,
    )
    write_cache(SCRAPE_CACHE, cache_key, result, resolve_cache_ttl_ms(None, DEFAULT_CACHE_TTL_MINUTES))
    return result


testing = {
    "assertFirecrawlScrapeTargetAllowed": assert_firecrawl_scrape_target_allowed,
    "parseFirecrawlScrapePayload": parse_firecrawl_scrape_payload,
    "postFirecrawlJson": _post_firecrawl_json,
    "readFirecrawlJsonResponse": read_provider_json_response,
    "resolveEndpoint": _resolve_endpoint,
    "validateFirecrawlBaseUrl": _validate_firecrawl_base_url,
    "resolveSearchItems": resolve_search_items,
}
