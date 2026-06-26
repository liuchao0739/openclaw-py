"""Managed proxy TLS helpers resolve and load CA trust only for HTTPS forward
proxies that OpenClaw owns or inherited from a parent process.

Mirrors src/infra/net/proxy/proxy-tls.ts.
"""

from __future__ import annotations

from typing import Any, Mapping, TypedDict
from urllib.parse import urlparse


class ManagedProxyTlsOptions(TypedDict, total=False):
    ca: str


def _normalize_optional_path(value: str | None) -> str | None:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed or None


def _format_read_error(err: Any) -> str:
    return str(err)


def _is_https_proxy_url(value: str | None) -> bool:
    if not value:
        return False
    try:
        parsed = urlparse(value)
        return parsed.scheme == "https"
    except Exception:
        return False


def resolve_managed_proxy_ca_file(
    params: Mapping[str, Any],
) -> str | None:
    """Resolve the configured managed proxy CA file, with env/CLI override first."""
    ca_file_override = _normalize_optional_path(params.get("caFileOverride"))
    if ca_file_override:
        return ca_file_override
    config = params.get("config")
    if isinstance(config, Mapping):
        tls = config.get("tls")
        if isinstance(tls, Mapping):
            return _normalize_optional_path(tls.get("caFile"))
    return None


def resolve_managed_proxy_ca_file_for_url(
    params: Mapping[str, Any],
) -> str | None:
    """Return a CA file only for HTTPS proxy URLs; HTTP proxies do not need TLS trust."""
    if not _is_https_proxy_url(params.get("proxyUrl")):
        return None
    return resolve_managed_proxy_ca_file(
        {"config": params.get("config"), "caFileOverride": params.get("caFileOverride")}
    )


async def load_managed_proxy_tls_options(
    ca_file: str | None,
) -> ManagedProxyTlsOptions | None:
    """Load managed proxy TLS options asynchronously for startup paths."""
    if not ca_file:
        return None
    try:
        with open(ca_file, "r", encoding="utf-8") as fh:
            return {"ca": fh.read()}
    except Exception as err:
        raise OSError(
            f"proxy CA file could not be read ({ca_file}): {_format_read_error(err)}"
        ) from err


def load_managed_proxy_tls_options_sync(
    ca_file: str | None,
) -> ManagedProxyTlsOptions | None:
    """Load managed proxy TLS options synchronously for inherited child-process routing."""
    if not ca_file:
        return None
    try:
        with open(ca_file, "r", encoding="utf-8") as fh:
            return {"ca": fh.read()}
    except Exception as err:
        raise OSError(
            f"proxy CA file could not be read ({ca_file}): {_format_read_error(err)}"
        ) from err
