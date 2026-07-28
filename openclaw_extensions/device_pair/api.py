from typing import Dict, Optional, Tuple, List
import socket
import os
import re


PAIRING_SETUP_BOOTSTRAP_PROFILE = "pairing-setup"


def normalize_optional_string(value: Optional[str]) -> Optional[str]:
    if value is None:
        return None
    return str(value).strip() or None


def normalize_lowercase_string_or_empty(value: Optional[str]) -> str:
    return value.strip().lower() if value else ""


def parseIPv4Octets(address: str) -> Optional[Tuple[int, int, int, int]]:
    parts = address.split(".")
    if len(parts) != 4:
        return None
    if not all(part.isdigit() for part in parts):
        return None
    octets = tuple(int(part) for part in parts)
    if any(not (0 <= value <= 255) for value in octets):
        return None
    return octets


def isPrivateIPv4(address: str) -> bool:
    octets = parseIPv4Octets(address)
    if not octets:
        return False
    a, b = octets[0], octets[1]
    if a == 10:
        return True
    if a == 172 and 16 <= b <= 31:
        return True
    if a == 192 and b == 168:
        return True
    return False


def isTailnetIPv4(address: str) -> bool:
    octets = parseIPv4Octets(address)
    if not octets:
        return False
    a, b = octets[0], octets[1]
    return a == 100 and 64 <= b <= 127


def pickMatchingIPv4(predicate) -> Optional[str]:
    try:
        for hostname in ["", socket.gethostname()]:
            try:
                addresses = socket.getaddrinfo(hostname, None, socket.AF_INET)
                for addrinfo in addresses:
                    address = addrinfo[4][0]
                    if predicate(address):
                        return address
            except socket.gaierror:
                continue
    except Exception:
        pass
    return None


def pickLanIPv4() -> Optional[str]:
    return pickMatchingIPv4(isPrivateIPv4)


def pickTailnetIPv4() -> Optional[str]:
    return pickMatchingIPv4(isTailnetIPv4)


def normalizeHostForIpCheck(host: str) -> str:
    normalized = normalize_lowercase_string_or_empty(host)
    if normalized.startswith("[") and normalized.endswith("]"):
        normalized = normalized[1:-1]
    if normalized.endswith("."):
        normalized = normalized[:-1]
    zone_index = normalized.find("%")
    if zone_index >= 0:
        normalized = normalized[:zone_index]
    return normalized


def isLoopbackHost(host: str) -> bool:
    normalized = normalizeHostForIpCheck(host)
    if not normalized:
        return False
    if normalized in ("localhost", "0.0.0.0", "::"):
        return True
    octets = parseIPv4Octets(normalized)
    if octets:
        return octets[0] == 127
    return normalized in ("::1", "0:0:0:0:0:0:0:1")


def isPrivateLanCleartextHost(host: str) -> bool:
    normalized = normalizeHostForIpCheck(host)
    if normalized.endswith(".local"):
        return True
    if isPrivateIPv4(normalized):
        return True
    octets = parseIPv4Octets(normalized)
    if octets:
        return octets[0] == 169 and octets[1] == 254
    return False


def isMobilePairingCleartextAllowedHost(host: str) -> bool:
    normalized = normalizeHostForIpCheck(host)
    return isLoopbackHost(normalized) or normalized == "10.0.2.2" or isPrivateLanCleartextHost(normalized)


GATEWAY_SCHEME_WITHOUT_AUTHORITY_RE = re.compile(r"^(?:https?|wss?):(?!\/\/)", re.IGNORECASE)
SCHEME_LIKE_PATH_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:\//")


def parseNormalizedGatewayUrl(raw: str) -> Optional[str]:
    try:
        from urllib.parse import urlparse
        parsed = urlparse(raw)
        if parsed.username or parsed.password:
            return None
        scheme = parsed.scheme
        if scheme == "http":
            normalized_scheme = "ws"
        elif scheme == "https":
            normalized_scheme = "wss"
        else:
            normalized_scheme = scheme
        if normalized_scheme not in ("ws", "wss"):
            return None
        if not parsed.hostname:
            return None
        port = f":{parsed.port}" if parsed.port else ""
        return f"{normalized_scheme}://{parsed.hostname}{port}"
    except Exception:
        return None


def normalizeUrl(raw: str, schemeFallback: str) -> Optional[str]:
    candidate = normalize_optional_string(raw)
    if not candidate:
        return None
    if GATEWAY_SCHEME_WITHOUT_AUTHORITY_RE.match(candidate):
        return None
    parsed_url = parseNormalizedGatewayUrl(candidate)
    if parsed_url:
        return parsed_url
    if "://" in candidate or SCHEME_LIKE_PATH_RE.match(candidate):
        return None
    host_port = normalize_optional_string(candidate.split("/", 1)[0]) or ""
    return parseNormalizedGatewayUrl(f"{schemeFallback}://{host_port}") if host_port else None


def describeSecureMobilePairingFix(source: Optional[str] = None) -> str:
    source_note = f" Resolved source: {source}." if source else ""
    return (
        "Tailscale and public mobile pairing require a secure gateway URL (wss://) or Tailscale Serve/Funnel."
        + source_note
        + " Fix: use a private LAN address, prefer gateway.tailscale.mode=serve, or set "
        + "gateway.remote.url / plugins.entries.device-pair.config.publicUrl to a wss:// URL. "
        + "ws:// setup codes are only valid for localhost/loopback, private LAN addresses, .local hosts, or the Android emulator."
    )


def validateMobilePairingUrl(url: str, source: Optional[str] = None) -> Optional[str]:
    from urllib.parse import urlparse
    try:
        parsed = urlparse(url)
    except Exception:
        return "Resolved mobile pairing URL is invalid."
    if parsed.scheme == "https":
        protocol = "wss"
    elif parsed.scheme == "http":
        protocol = "ws"
    else:
        protocol = parsed.scheme
    if protocol == "wss":
        return None
    if protocol == "ws" and isMobilePairingCleartextAllowedHost(parsed.hostname or ""):
        return None
    return describeSecureMobilePairingFix(source)


def resolveScheme(cfg: Dict, opts: Optional[Dict] = None) -> str:
    if opts and opts.get("forceSecure"):
        return "wss"
    return "wss" if cfg.get("gateway", {}).get("tls", {}).get("enabled") else "ws"


def resolveGatewayPort(cfg: Dict) -> int:
    return cfg.get("gateway", {}).get("port", 3001)


def resolveGatewayBindUrl(params: Dict) -> Optional[Dict]:
    bind = params.get("bind", "127.0.0.1")
    custom_bind_host = params.get("customBindHost")
    scheme = params.get("scheme", "ws")
    port = params.get("port", 3001)
    pickTailnetHost = params.get("pickTailnetHost")
    pickLanHost = params.get("pickLanHost")

    bind_address = custom_bind_host or bind

    if bind_address == "lan":
        lan_ip = pickLanHost() if pickLanHost else pickLanIPv4()
        if lan_ip:
            return {"url": f"{scheme}://{lan_ip}:{port}", "source": "lan"}
        tailnet_ip = pickTailnetHost() if pickTailnetHost else pickTailnetIPv4()
        if tailnet_ip:
            return {"url": f"{scheme}://{tailnet_ip}:{port}", "source": "tailnet"}
        return None

    if bind_address in ("0.0.0.0", "::", "*"):
        lan_ip = pickLanHost() if pickLanHost else pickLanIPv4()
        if lan_ip:
            return {"url": f"{scheme}://{lan_ip}:{port}", "source": "lan"}
        return None

    return {"url": f"{scheme}://{bind_address}:{port}", "source": "bind"}


def resolvePreferredOpenClawTmpDir() -> str:
    return os.path.join(os.path.expanduser("~"), ".openclaw", "tmp")


def issueDeviceBootstrapToken(params: Dict) -> Dict:
    import time
    import secrets
    expires_at_ms = int(time.time() * 1000) + 15 * 60 * 1000
    return {
        "token": secrets.token_urlsafe(32),
        "expiresAtMs": expires_at_ms,
    }


def clearDeviceBootstrapTokens() -> Dict:
    return {"removed": 0}


def revokeDeviceBootstrapToken(params: Dict) -> bool:
    return True


def listDevicePairing() -> Dict:
    return {"pending": []}


def approveDevicePairing(request_id: str, params: Optional[Dict] = None) -> Optional[Dict]:
    return None


__all__ = [
    "PAIRING_SETUP_BOOTSTRAP_PROFILE",
    "issueDeviceBootstrapToken",
    "clearDeviceBootstrapTokens",
    "revokeDeviceBootstrapToken",
    "listDevicePairing",
    "approveDevicePairing",
    "resolveGatewayBindUrl",
    "resolveGatewayPort",
    "resolveScheme",
    "normalizeUrl",
    "validateMobilePairingUrl",
    "normalizeHostForIpCheck",
    "isLoopbackHost",
    "isPrivateLanCleartextHost",
    "isMobilePairingCleartextAllowedHost",
    "pickLanIPv4",
    "pickTailnetIPv4",
    "resolvePreferredOpenClawTmpDir",
]