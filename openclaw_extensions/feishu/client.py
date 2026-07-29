import platform
from typing import Any, Optional

from .types import FeishuDomain, ResolvedFeishuAccount

PLUGIN_VERSION = "2026.6.10"

FEISHU_USER_AGENT = f"openclaw-feishu-builtin/{PLUGIN_VERSION}/{platform.system().lower()}"

FEISHU_HTTP_TIMEOUT_MS = 30000
FEISHU_HTTP_TIMEOUT_MAX_MS = 120000
FEISHU_HTTP_TIMEOUT_ENV_VAR = "FEISHU_HTTP_TIMEOUT_MS"

FEISHU_WS_CONFIG = {
    "PingInterval": 30,
    "PingTimeout": 3,
}


def get_feishu_user_agent() -> str:
    return FEISHU_USER_AGENT


def resolve_configured_http_timeout_ms(creds: dict) -> int:
    raw = creds.get("httpTimeoutMs")
    if isinstance(raw, int) and raw > 0:
        return min(raw, FEISHU_HTTP_TIMEOUT_MAX_MS)
    import os
    env_value = os.environ.get(FEISHU_HTTP_TIMEOUT_ENV_VAR)
    if env_value:
        try:
            parsed = int(env_value)
            if parsed > 0:
                return min(parsed, FEISHU_HTTP_TIMEOUT_MAX_MS)
        except ValueError:
            pass
    return FEISHU_HTTP_TIMEOUT_MS


def resolve_domain(domain: Optional[str]) -> str:
    if domain == "lark":
        return "https://open.larksuite.com"
    if domain == "feishu" or not domain:
        return "https://open.feishu.cn"
    return domain.rstrip("/")


class FeishuClientCredentials(dict):
    pass


_client_cache: dict = {}


def create_feishu_client(creds: dict) -> Any:
    try:
        import lark_oapi as lark
    except ImportError:
        lark = None

    account_id = creds.get("accountId") or "default"
    app_id = creds.get("appId")
    app_secret = creds.get("appSecret")
    domain = creds.get("domain")
    default_http_timeout_ms = resolve_configured_http_timeout_ms(creds)

    if not app_id or not app_secret:
        raise ValueError(f'Feishu credentials not configured for account "{account_id}"')

    cached = _client_cache.get(account_id)
    if (
        cached
        and cached["config"]["appId"] == app_id
        and cached["config"]["appSecret"] == app_secret
        and cached["config"]["domain"] == domain
        and cached["config"]["httpTimeoutMs"] == default_http_timeout_ms
    ):
        return cached["client"]

    if lark is None:
        client = {
            "appId": app_id,
            "appSecret": app_secret,
            "domain": resolve_domain(domain),
            "timeout": default_http_timeout_ms,
        }
    else:
        client = lark.Client.builder().app_id(app_id).app_secret(app_secret).domain(resolve_domain(domain)).build()

    _client_cache[account_id] = {
        "client": client,
        "config": {"appId": app_id, "appSecret": app_secret, "domain": domain, "httpTimeoutMs": default_http_timeout_ms},
    }
    return client


async def create_feishu_ws_client(account: ResolvedFeishuAccount, callbacks: Optional[dict] = None) -> Any:
    try:
        import lark_oapi as lark
    except ImportError:
        lark = None

    account_id = account.get("accountId")
    app_id = account.get("appId")
    app_secret = account.get("appSecret")
    domain = account.get("domain")

    if not app_id or not app_secret:
        raise ValueError(f'Feishu credentials not configured for account "{account_id}"')

    if lark is None:
        return {
            "appId": app_id,
            "appSecret": app_secret,
            "domain": resolve_domain(domain),
            "wsConfig": FEISHU_WS_CONFIG,
        }
    return lark.ws.Client(app_id, app_secret, domain=resolve_domain(domain))


def create_event_dispatcher(account: ResolvedFeishuAccount) -> Any:
    try:
        import lark_oapi as lark
    except ImportError:
        lark = None

    encrypt_key = account.get("encryptKey")
    verification_token = account.get("verificationToken")
    if lark is None:
        return {"encryptKey": encrypt_key, "verificationToken": verification_token}
    return lark.EventDispatcherHandler.builder(encrypt_key, verification_token).build()


def clear_client_cache(account_id: Optional[str] = None) -> None:
    if account_id:
        _client_cache.pop(account_id, None)
    else:
        _client_cache.clear()
