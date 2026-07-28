from __future__ import annotations

import asyncio
import json
import os
import re
import ssl
import time
import uuid
from typing import Any, Callable, Optional

from websockets.asyncio.client import connect as websockets_connect
from websockets.exceptions import ConnectionClosed

from openclaw.packages.gateway_protocol.client_info import (
    GATEWAY_CLIENT_NAMES,
)
from openclaw.packages.gateway_protocol.version import (
    MIN_CLIENT_PROTOCOL_VERSION,
    PROTOCOL_VERSION,
)
from openclaw.packages.net_policy.ip import (
    is_loopback_ip_address,
    is_private_or_loopback_ip_address,
    parse_canonical_ip_address,
)

from ._protocol_helpers import (
    format_connect_error_message,
    read_connect_error_detail_code,
    read_connect_error_recovery_advice,
    read_pairing_connect_error_details,
    resolve_gateway_startup_retry_after_ms,
)
from .device_auth import build_device_auth_payload_v3
from .timeouts import (
    resolve_connect_challenge_timeout_ms,
    resolve_safe_timeout_delay_ms,
)

_DEFAULT_GATEWAY_CLIENT_URL = "ws://127.0.0.1:18789"
_DEFAULT_CLIENT_VERSION = "0.0.0"

_GATEWAY_CLOSE_CODE_HINTS = {
    1000: "normal closure",
    1006: "abnormal closure (no close frame)",
    1008: "policy violation",
    1012: "service restart",
    1013: "try again later",
}

_FORCE_STOP_TERMINATE_GRACE_MS = 250
_STOP_AND_WAIT_TIMEOUT_MS = 1_000
_MAX_SUPPRESSED_TRANSIENT_PRE_HELLO_CLEAN_CLOSES = 1

_SENSITIVE_QUERY_PARAM_RE = re.compile(
    r"(?:token|password|secret|key|auth|credential)", re.IGNORECASE
)

_URL_USERINFO_RE = re.compile(r"//([^@/?#\s]+)@")
_URL_AUTH_BEARER_RE = re.compile(r"(Authorization:\s*Bearer\s+)[^\s]+", re.IGNORECASE)
_URL_QUERY_PARAM_RE = re.compile(r"([?&])([^=&\s]+)=([^&#\s\"'<>)]*)")


class DeviceIdentity:
    def __init__(self, *, device_id: str, private_key_pem: str, public_key_pem: str):
        self.device_id = device_id
        self.private_key_pem = private_key_pem
        self.public_key_pem = public_key_pem


class DeviceAuthTokenRecord:
    def __init__(self, *, token: Optional[str] = None, scopes: Optional[list[str]] = None):
        self.token = token
        self.scopes = scopes


class GatewayClientHostDeps:
    def __init__(
        self,
        *,
        load_or_create_device_identity: Optional[Callable[[], Optional[DeviceIdentity]]] = None,
        sign_device_payload: Optional[Callable[[str, str], str]] = None,
        public_key_raw_base64url_from_pem: Optional[Callable[[str], str]] = None,
        load_device_auth_token: Optional[Callable[[dict], Optional[DeviceAuthTokenRecord]]] = None,
        store_device_auth_token: Optional[Callable[[dict], None]] = None,
        clear_device_auth_token: Optional[Callable[[dict], None]] = None,
        before_connect: Optional[Callable[[], None]] = None,
        register_gateway_loopback_bypass: Optional[Callable[[str], Optional[Callable[[], None]]]] = None,
        log_debug: Optional[Callable[[str], None]] = None,
        log_error: Optional[Callable[[str], None]] = None,
        redact_for_log: Optional[Callable[[str], str]] = None,
        normalize_tls_fingerprint: Optional[Callable[[str], str]] = None,
    ):
        self.load_or_create_device_identity = load_or_create_device_identity
        self.sign_device_payload = sign_device_payload
        self.public_key_raw_base64url_from_pem = public_key_raw_base64url_from_pem
        self.load_device_auth_token = load_device_auth_token
        self.store_device_auth_token = store_device_auth_token
        self.clear_device_auth_token = clear_device_auth_token
        self.before_connect = before_connect
        self.register_gateway_loopback_bypass = register_gateway_loopback_bypass
        self.log_debug = log_debug
        self.log_error = log_error
        self.redact_for_log = redact_for_log
        self.normalize_tls_fingerprint = normalize_tls_fingerprint


class GatewayClientRequestError(Exception):
    def __init__(self, error: dict):
        message = error.get("message", "unknown error")
        details = error.get("details")
        formatted = format_connect_error_message({"message": message, "details": details})
        super().__init__(formatted)
        self.name = "GatewayClientRequestError"
        self.gateway_code = error.get("code") or "UNAVAILABLE"
        self.details = details
        self.retryable = error.get("retryable") is True
        self.retry_after_ms = error.get("retryAfterMs")


class GatewayClientTransientPreHelloCloseError(Exception):
    def __init__(self):
        super().__init__("gateway transient pre-hello clean close")
        self.name = "GatewayClientTransientPreHelloCloseError"


class GatewayClientRequestOptions:
    def __init__(
        self,
        *,
        expect_final: Optional[bool] = None,
        timeout_ms: Optional[int] = None,
        abort_event: Optional[asyncio.Event] = None,
        on_accepted: Optional[Callable[[Any], None]] = None,
    ):
        self.expect_final = expect_final
        self.timeout_ms = timeout_ms
        self.abort_event = abort_event
        self.on_accepted = on_accepted


class GatewayReconnectPausedInfo:
    def __init__(self, *, code: int, reason: str, detail_code: Optional[str]):
        self.code = code
        self.reason = reason
        self.detail_code = detail_code


class GatewayClientCloseInfo:
    def __init__(
        self,
        *,
        phase: str,
        socket_opened: bool,
        transport_validated: bool,
        transient_pre_hello_clean_close: bool,
    ):
        self.phase = phase
        self.socket_opened = socket_opened
        self.transport_validated = transport_validated
        self.transient_pre_hello_clean_close = transient_pre_hello_clean_close


class GatewayClientOptions:
    def __init__(
        self,
        *,
        url: Optional[str] = None,
        connect_challenge_timeout_ms: Optional[int] = None,
        connect_delay_ms: Optional[int] = None,
        preauth_handshake_timeout_ms: Optional[int] = None,
        tick_watch_min_interval_ms: Optional[int] = None,
        tick_watch_timeout_ms: Optional[int] = None,
        request_timeout_ms: Optional[int] = None,
        token: Optional[str] = None,
        bootstrap_token: Optional[str] = None,
        device_token: Optional[str] = None,
        password: Optional[str] = None,
        approval_runtime_token: Optional[str] = None,
        instance_id: Optional[str] = None,
        client_name: Optional[str] = None,
        client_display_name: Optional[str] = None,
        client_version: Optional[str] = None,
        platform: Optional[str] = None,
        device_family: Optional[str] = None,
        mode: Optional[str] = None,
        role: Optional[str] = None,
        scopes: Optional[list[str]] = None,
        caps: Optional[list[str]] = None,
        commands: Optional[list[str]] = None,
        permissions: Optional[dict[str, bool]] = None,
        path_env: Optional[str] = None,
        env: Optional[dict] = None,
        device_identity: Optional[DeviceIdentity] = None,
        host_deps: Optional[GatewayClientHostDeps] = None,
        min_protocol: Optional[int] = None,
        max_protocol: Optional[int] = None,
        tls_fingerprint: Optional[str] = None,
        on_event: Optional[Callable[[dict], None]] = None,
        on_hello_ok: Optional[Callable[[dict], None]] = None,
        on_connect_error: Optional[Callable[[Exception], None]] = None,
        on_reconnect_paused: Optional[Callable[[GatewayReconnectPausedInfo], None]] = None,
        on_close: Optional[Callable[[int, str, Optional[GatewayClientCloseInfo]], None]] = None,
        on_gap: Optional[Callable[[dict], None]] = None,
    ):
        self.url = url
        self.connect_challenge_timeout_ms = connect_challenge_timeout_ms
        self.connect_delay_ms = connect_delay_ms
        self.preauth_handshake_timeout_ms = preauth_handshake_timeout_ms
        self.tick_watch_min_interval_ms = tick_watch_min_interval_ms
        self.tick_watch_timeout_ms = tick_watch_timeout_ms
        self.request_timeout_ms = request_timeout_ms
        self.token = token
        self.bootstrap_token = bootstrap_token
        self.device_token = device_token
        self.password = password
        self.approval_runtime_token = approval_runtime_token
        self.instance_id = instance_id
        self.client_name = client_name
        self.client_display_name = client_display_name
        self.client_version = client_version
        self.platform = platform
        self.device_family = device_family
        self.mode = mode
        self.role = role
        self.scopes = scopes
        self.caps = caps
        self.commands = commands
        self.permissions = permissions
        self.path_env = path_env
        self.env = env
        self.device_identity = device_identity
        self.host_deps = host_deps
        self.min_protocol = min_protocol
        self.max_protocol = max_protocol
        self.tls_fingerprint = tls_fingerprint
        self.on_event = on_event
        self.on_hello_ok = on_hello_ok
        self.on_connect_error = on_connect_error
        self.on_reconnect_paused = on_reconnect_paused
        self.on_close = on_close
        self.on_gap = on_gap


class GatewayClient:
    def __init__(self, options: GatewayClientOptions):
        host_deps = options.host_deps or GatewayClientHostDeps()
        noop = lambda: None
        self._deps = GatewayClientHostDeps(
            load_or_create_device_identity=host_deps.load_or_create_device_identity or (lambda: None),
            sign_device_payload=host_deps.sign_device_payload or self._throw_device_signing_error,
            public_key_raw_base64url_from_pem=host_deps.public_key_raw_base64url_from_pem or self._throw_public_key_error,
            load_device_auth_token=host_deps.load_device_auth_token or (lambda _p: None),
            store_device_auth_token=host_deps.store_device_auth_token or (lambda _p: None),
            clear_device_auth_token=host_deps.clear_device_auth_token or (lambda _p: None),
            before_connect=host_deps.before_connect or noop,
            register_gateway_loopback_bypass=host_deps.register_gateway_loopback_bypass or (lambda _u: None),
            log_debug=host_deps.log_debug or noop,
            log_error=host_deps.log_error or noop,
            redact_for_log=host_deps.redact_for_log or (lambda m: m),
            normalize_tls_fingerprint=host_deps.normalize_tls_fingerprint or self._normalize_fingerprint,
        )

        device_identity = options.device_identity
        if device_identity is None and host_deps.load_or_create_device_identity:
            device_identity = host_deps.load_or_create_device_identity()

        self._options = GatewayClientOptions(
            url=options.url,
            connect_challenge_timeout_ms=options.connect_challenge_timeout_ms,
            connect_delay_ms=options.connect_delay_ms,
            preauth_handshake_timeout_ms=options.preauth_handshake_timeout_ms,
            tick_watch_min_interval_ms=options.tick_watch_min_interval_ms,
            tick_watch_timeout_ms=options.tick_watch_timeout_ms,
            request_timeout_ms=options.request_timeout_ms,
            token=options.token,
            bootstrap_token=options.bootstrap_token,
            device_token=options.device_token,
            password=options.password,
            approval_runtime_token=options.approval_runtime_token,
            instance_id=options.instance_id,
            client_name=options.client_name,
            client_display_name=options.client_display_name,
            client_version=options.client_version,
            platform=options.platform,
            device_family=options.device_family,
            mode=options.mode,
            role=options.role,
            scopes=options.scopes,
            caps=options.caps,
            commands=options.commands,
            permissions=options.permissions,
            path_env=options.path_env,
            env=options.env,
            device_identity=device_identity,
            host_deps=options.host_deps,
            min_protocol=options.min_protocol,
            max_protocol=options.max_protocol,
            tls_fingerprint=options.tls_fingerprint,
            on_event=options.on_event,
            on_hello_ok=options.on_hello_ok,
            on_connect_error=options.on_connect_error,
            on_reconnect_paused=options.on_reconnect_paused,
            on_close=options.on_close,
            on_gap=options.on_gap,
        )

        request_timeout_ms = options.request_timeout_ms
        if request_timeout_ms is not None and request_timeout_ms == int(request_timeout_ms):
            self._request_timeout_ms = resolve_safe_timeout_delay_ms(int(request_timeout_ms), min_ms=0)
        else:
            self._request_timeout_ms = 30_000

        self._ws = None
        self._pending: dict[str, dict[str, Any]] = {}
        self._backoff_ms = 1000
        self._closed = False
        self._last_seq: Optional[int] = None
        self._connect_nonce: Optional[str] = None
        self._connect_sent = False
        self._connect_timer: Optional[asyncio.Task] = None
        self._reconnect_timer: Optional[asyncio.Task] = None
        self._pending_device_token_retry = False
        self._device_token_retry_budget_used = False
        self._approval_runtime_token_compatibility_disabled = False
        self._approval_runtime_token_retry_budget_used = False
        self._pending_startup_reconnect_delay_ms: Optional[int] = None
        self._pending_connect_error_detail_code: Optional[str] = None
        self._pending_connect_error_details: Any = None
        self._last_tick: Optional[float] = None
        self._tick_interval_ms = 30_000
        self._tick_timer: Optional[asyncio.Task] = None
        self._pending_stop: Optional[dict[str, Any]] = None
        self._socket_opened = False
        self._transport_validated = False
        self._hello_ok_received = False
        self._suppressed_transient_pre_hello_clean_closes = 0

    @staticmethod
    def _throw_device_signing_error(_k: str, _p: str) -> str:
        raise Exception("GatewayClient device signature dependency is not configured")

    @staticmethod
    def _throw_public_key_error(_p: str) -> str:
        raise Exception("GatewayClient public key dependency is not configured")

    @staticmethod
    def _normalize_fingerprint(fingerprint: str) -> str:
        return fingerprint.replace(":", "").strip().lower()

    @staticmethod
    def _normalize_optional_string(value: Any) -> Optional[str]:
        if not isinstance(value, str):
            return None
        trimmed = value.strip()
        return trimmed or None

    @staticmethod
    def _is_record(value: Any) -> bool:
        return bool(value) and isinstance(value, dict)

    @staticmethod
    def _is_non_empty_string(value: Any) -> bool:
        return isinstance(value, str) and len(value) > 0

    @staticmethod
    def _is_non_negative_integer(value: Any) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    @staticmethod
    def _is_gateway_client_error_shape(value: Any) -> bool:
        if not GatewayClient._is_record(value):
            return False
        if not GatewayClient._is_non_empty_string(value.get("code")) or not GatewayClient._is_non_empty_string(value.get("message")):
            return False
        retryable = value.get("retryable")
        if retryable is not None and not isinstance(retryable, bool):
            return False
        retry_after_ms = value.get("retryAfterMs")
        if retry_after_ms is not None and not GatewayClient._is_non_negative_integer(retry_after_ms):
            return False
        return True

    @staticmethod
    def _is_gateway_event_frame(value: Any) -> bool:
        if not GatewayClient._is_record(value) or value.get("type") != "event":
            return False
        if not GatewayClient._is_non_empty_string(value.get("event")):
            return False
        seq = value.get("seq")
        return seq is None or GatewayClient._is_non_negative_integer(seq)

    @staticmethod
    def _is_gateway_response_frame(value: Any) -> bool:
        if (
            not GatewayClient._is_record(value)
            or value.get("type") != "res"
            or not GatewayClient._is_non_empty_string(value.get("id"))
            or not isinstance(value.get("ok"), bool)
        ):
            return False
        error = value.get("error")
        return error is None or GatewayClient._is_gateway_client_error_shape(error)

    @staticmethod
    def _validate_client_request_frame(frame: dict) -> Optional[str]:
        if not GatewayClient._is_non_empty_string(frame.get("id")):
            return "id must be a non-empty string"
        if not GatewayClient._is_non_empty_string(frame.get("method")):
            return "method must be a non-empty string"
        return None

    @staticmethod
    def _normalize_lowercase_string_or_empty(value: Any) -> str:
        if isinstance(value, str):
            return value.strip().lower()
        return ""

    @staticmethod
    def _raw_data_to_string(data: Any) -> str:
        if isinstance(data, str):
            return data
        if isinstance(data, bytes):
            return data.decode("utf-8")
        if isinstance(data, bytearray):
            return data.decode("utf-8")
        if isinstance(data, memoryview):
            return bytes(data).decode("utf-8")
        if isinstance(data, list):
            parts = []
            for entry in data:
                if isinstance(entry, bytes):
                    parts.append(entry)
                elif isinstance(entry, str):
                    parts.append(entry.encode("utf-8"))
                else:
                    parts.append(str(entry).encode("utf-8"))
            return b"".join(parts).decode("utf-8")
        return str(data)

    @staticmethod
    def _is_sensitive_url_query_param_name(key: str) -> bool:
        return bool(_SENSITIVE_QUERY_PARAM_RE.search(key))

    @staticmethod
    def _parse_host_for_address_checks(host: str) -> Optional[dict]:
        if not host:
            return None
        normalized = host.lower().strip()
        canonical = normalized.rstrip(".")
        if canonical == "localhost":
            return {"isLocalhost": True, "unbracketedHost": canonical}
        unbracketed = normalized
        if normalized.startswith("[") and normalized.endswith("]"):
            unbracketed = normalized[1:-1]
        return {"isLocalhost": False, "unbracketedHost": unbracketed}

    @staticmethod
    def _is_loopback_host(host: str) -> bool:
        parsed = GatewayClient._parse_host_for_address_checks(host)
        if not parsed:
            return False
        if parsed["isLocalhost"]:
            return True
        address = parse_canonical_ip_address(parsed["unbracketedHost"])
        if not address:
            return False
        return is_loopback_ip_address(str(address))

    @staticmethod
    def _is_private_or_loopback_host(host: str) -> bool:
        parsed = GatewayClient._parse_host_for_address_checks(host)
        if not parsed:
            return False
        if parsed["isLocalhost"]:
            return True
        address = parse_canonical_ip_address(parsed["unbracketedHost"])
        if not address:
            return False
        return is_private_or_loopback_ip_address(str(address))

    @staticmethod
    def _is_trusted_plaintext_websocket_host(hostname: str) -> bool:
        if GatewayClient._is_private_or_loopback_host(hostname):
            return True
        normalized = hostname.lower().strip().rstrip(".")
        return normalized.endswith(".local") or normalized.endswith(".ts.net")

    @staticmethod
    def _is_secure_websocket_url(raw_url: str, *, allow_private_ws: bool = False) -> bool:
        try:
            from urllib.parse import urlparse
            parsed = urlparse(raw_url)
            protocol = parsed.scheme
            if protocol == "https":
                protocol = "wss"
            elif protocol == "http":
                protocol = "ws"
            if protocol == "wss":
                return True
            if protocol != "ws":
                return False
            hostname = parsed.hostname or ""
            if GatewayClient._is_loopback_host(hostname) or GatewayClient._is_trusted_plaintext_websocket_host(hostname):
                return True
            if allow_private_ws:
                host_for_ip_check = hostname
                if hostname.startswith("[") and hostname.endswith("]"):
                    host_for_ip_check = hostname[1:-1]
                return GatewayClient._is_private_or_loopback_host(hostname) or parse_canonical_ip_address(host_for_ip_check) is None
            return False
        except Exception:
            return False

    @staticmethod
    def _describe_gateway_close_code(code: int) -> Optional[str]:
        return _GATEWAY_CLOSE_CODE_HINTS.get(code)

    @staticmethod
    def _read_connect_challenge_timeout_override(opts: GatewayClientOptions) -> Optional[int]:
        val = opts.connect_challenge_timeout_ms
        if val is not None and val == int(val) and val == val:
            return int(val)
        val = opts.connect_delay_ms
        if val is not None and val == int(val) and val == val:
            return int(val)
        return None

    @staticmethod
    def _is_gateway_client_stopped_error(err: Any) -> bool:
        return str(err) in ("gateway client stopped", "Error: gateway client stopped")

    @staticmethod
    def _format_gateway_client_error_for_log(err: Any) -> str:
        s = str(err)
        s = _URL_USERINFO_RE.sub(r"//***:***@", s)
        s = _URL_AUTH_BEARER_RE.sub(r"\1***", s)

        def _replace_query_param(match: re.Match) -> str:
            prefix = match.group(1)
            key = match.group(2)
            if GatewayClient._is_sensitive_url_query_param_name(key):
                return f"{prefix}{key}=***"
            return match.group(0)

        s = _URL_QUERY_PARAM_RE.sub(_replace_query_param, s)
        return s

    def _log_debug(self, message: str) -> None:
        self._deps.log_debug(self._deps.redact_for_log(message))

    def _log_error(self, message: str) -> None:
        self._deps.log_error(self._deps.redact_for_log(message))

    def _notify_connect_error(self, error: Exception) -> None:
        handler = self._options.on_connect_error
        if handler:
            try:
                handler(error)
            except Exception as err:
                self._log_debug(
                    f"gateway client connect error handler error: {self._format_gateway_client_error_for_log(err)}"
                )

    def _notify_hello_ok(self, hello_ok: dict) -> None:
        handler = self._options.on_hello_ok
        if handler:
            try:
                handler(hello_ok)
            except Exception as err:
                self._log_debug(
                    f"gateway client hello-ok handler error: {self._format_gateway_client_error_for_log(err)}"
                )

    def _notify_reconnect_paused(self, info: GatewayReconnectPausedInfo) -> None:
        handler = self._options.on_reconnect_paused
        if handler:
            try:
                handler(info)
            except Exception as err:
                self._log_debug(
                    f"gateway client reconnect paused handler error: {self._format_gateway_client_error_for_log(err)}"
                )

    def _notify_close(
        self,
        code: int,
        reason: str,
        info: Optional[GatewayClientCloseInfo] = None,
    ) -> None:
        handler = self._options.on_close
        if handler:
            try:
                if info is None:
                    handler(code, reason)
                else:
                    handler(code, reason, info)
            except Exception as err:
                self._log_debug(
                    f"gateway client close handler error: {self._format_gateway_client_error_for_log(err)}"
                )

    def _resolve_gateway_client_connect_challenge_timeout_ms(self) -> int:
        override = self._read_connect_challenge_timeout_override(self._options)
        return resolve_connect_challenge_timeout_ms(
            override,
            params={
                "env": self._options.env,
                "configuredTimeoutMs": self._options.preauth_handshake_timeout_ms,
            },
        )

    async def start(self) -> None:
        if self._closed:
            return
        self._clear_reconnect_timer()
        self._clear_connect_challenge_timeout()
        self._connect_nonce = None
        self._connect_sent = False

        url = self._options.url or _DEFAULT_GATEWAY_CLIENT_URL

        if self._options.tls_fingerprint and not url.startswith("wss://"):
            self._notify_connect_error(
                Exception("gateway tls fingerprint requires wss:// gateway url")
            )
            return

        env = self._options.env or os.environ
        allow_private_ws = env.get("OPENCLAW_ALLOW_INSECURE_PRIVATE_WS") == "1"

        if not self._is_secure_websocket_url(url, allow_private_ws=allow_private_ws):
            display_host = url
            try:
                from urllib.parse import urlparse
                parsed = urlparse(url)
                if parsed.hostname:
                    display_host = parsed.hostname
            except Exception:
                pass

            msg = (
                f'SECURITY ERROR: Cannot connect to "{display_host}" over plaintext ws://. '
                "Both credentials and chat data would be exposed to network interception. "
                "Use wss:// for remote URLs. Safe defaults: keep gateway.bind=loopback and connect via SSH tunnel "
                "(ssh -N -L 18789:127.0.0.1:18789 user@gateway-host), or use Tailscale Serve/Funnel. "
            )
            if not allow_private_ws:
                msg += "Break-glass (trusted private networks only): set OPENCLAW_ALLOW_INSECURE_PRIVATE_WS=1. "
            msg += "Run `openclaw doctor --fix` for guidance."

            self._notify_connect_error(Exception(msg))
            return

        self._deps.before_connect()

        self._socket_opened = False
        self._transport_validated = False
        self._hello_ok_received = False
        self._connect_nonce = None
        self._connect_sent = False
        self._clear_connect_challenge_timeout()

        self._receive_task = asyncio.create_task(self._connect_and_receive(url))

    async def _connect_and_receive(self, url: str) -> None:
        ssl_context = None
        use_tls = url.startswith("wss://")

        if use_tls and self._options.tls_fingerprint:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE

        try:
            ws = await websockets_connect(
                url,
                ssl=ssl_context,
                max_size=25 * 1024 * 1024,
            )
        except Exception as err:
            self._notify_connect_error(err if isinstance(err, Exception) else Exception(str(err)))
            return

        self._ws = ws
        self._socket_opened = True

        if use_tls and self._options.tls_fingerprint:
            tls_error = self._validate_tls_fingerprint(ws)
            if tls_error:
                self._notify_connect_error(tls_error)
                try:
                    await ws.close(code=1008, reason=tls_error.args[0] if tls_error.args else "TLS fingerprint error")
                except Exception:
                    pass
                return

        self._transport_validated = True
        self._begin_preauth_handshake()

        try:
            async for raw_message in ws:
                message_str = self._raw_data_to_string(raw_message)
                self._handle_message(message_str)
        except ConnectionClosed as e:
            code = e.code if hasattr(e, 'code') and e.code else 1006
            reason = e.reason if hasattr(e, 'reason') and e.reason else ""
            await self._on_ws_close(code, reason)
        except Exception as err:
            self._log_debug(f"gateway client error: {self._format_gateway_client_error_for_log(err)}")
            if not self._connect_sent:
                self._notify_connect_error(err if isinstance(err, Exception) else Exception(str(err)))
            await self._on_ws_close(1006, str(err))

    async def _on_ws_close(self, code: int, reason: str) -> None:
        close_info = GatewayClientCloseInfo(
            phase="post-hello" if self._hello_ok_received else "pre-hello",
            socket_opened=self._socket_opened,
            transport_validated=self._transport_validated,
            transient_pre_hello_clean_close=(
                not self._hello_ok_received and code == 1000 and reason == ""
            ),
        )

        connect_error_detail_code = self._pending_connect_error_detail_code
        connect_error_details = self._pending_connect_error_details
        self._pending_connect_error_detail_code = None
        self._pending_connect_error_details = None

        if self._ws and hasattr(self._ws, 'wait_closed'):
            try:
                await self._ws.wait_closed()
            except Exception:
                pass
        self._ws = None

        self._socket_opened = False
        self._transport_validated = False
        self._resolve_pending_stop()

        if self._pending_startup_reconnect_delay_ms is not None:
            self._schedule_reconnect()
            return

        if (
            close_info.transient_pre_hello_clean_close
            and self._suppressed_transient_pre_hello_clean_closes
            < _MAX_SUPPRESSED_TRANSIENT_PRE_HELLO_CLEAN_CLOSES
        ):
            self._suppressed_transient_pre_hello_clean_closes += 1
            self._flush_pending_errors(GatewayClientTransientPreHelloCloseError())
            self._schedule_reconnect()
            self._notify_close(code, reason, close_info)
            return

        if (
            code == 1008
            and "device token mismatch" in self._normalize_lowercase_string_or_empty(reason)
            and not self._options.token
            and not self._options.password
            and self._options.device_identity
        ):
            device_id = self._options.device_identity.device_id
            role = self._options.role or "operator"
            try:
                self._deps.clear_device_auth_token({
                    "deviceId": device_id,
                    "role": role,
                    "env": self._options.env,
                })
                self._log_debug(f"cleared stale device-auth token for device {device_id}")
            except Exception as err:
                self._log_debug(
                    f"failed clearing stale device-auth token for device {device_id}: {str(err)}"
                )

        self._flush_pending_errors(Exception(f"gateway closed ({code}): {reason}"))

        if self._should_pause_reconnect_after_auth_failure(
            detail_code=connect_error_detail_code,
            details=connect_error_details,
        ):
            self._notify_reconnect_paused(
                GatewayReconnectPausedInfo(
                    code=code,
                    reason=reason,
                    detail_code=connect_error_detail_code,
                )
            )
            self._notify_close(code, reason, close_info)
            return

        self._schedule_reconnect()
        self._notify_close(code, reason, close_info)

    def _validate_tls_fingerprint(self, ws: Any) -> Optional[Exception]:
        if not self._options.tls_fingerprint or not ws:
            return None
        expected = self._deps.normalize_tls_fingerprint(self._options.tls_fingerprint)
        if not expected:
            return Exception("gateway tls fingerprint missing")

        fingerprint = ""
        try:
            if hasattr(ws, 'get_extra_info'):
                sock = ws.get_extra_info('socket')
                if sock:
                    der_cert = sock.getpeercert(True)
                    if der_cert:
                        import hashlib
                        sha256 = hashlib.sha256(der_cert).hexdigest()
                        fingerprint = self._deps.normalize_tls_fingerprint(sha256)
        except Exception:
            pass

        if not fingerprint:
            return Exception("gateway tls fingerprint unavailable")
        if fingerprint != expected:
            return Exception("gateway tls fingerprint mismatch")
        return None

    async def stop(self) -> None:
        await self._begin_stop()

    async def stop_and_wait(self, *, timeout_ms: Optional[int] = None) -> None:
        stop_promise = await self._begin_stop()
        if stop_promise is None:
            return

        if timeout_ms is None:
            timeout_ms = _STOP_AND_WAIT_TIMEOUT_MS
        else:
            timeout_ms = resolve_safe_timeout_delay_ms(timeout_ms)

        try:
            timeout_event = asyncio.Event()

            async def _timeout_handler():
                await asyncio.sleep(timeout_ms / 1000.0)
                timeout_event.set()

            timeout_task = asyncio.create_task(_timeout_handler())

            try:
                done, pending = await asyncio.wait(
                    [stop_promise, timeout_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                if timeout_task in done:
                    raise Exception(f"gateway client stop timed out after {timeout_ms}ms")
                for task in pending:
                    task.cancel()
            except asyncio.CancelledError:
                timeout_task.cancel()
                raise
        finally:
            timeout_task.cancel()

    async def _begin_stop(self) -> Optional[asyncio.Future]:
        self._closed = True
        self._pending_device_token_retry = False
        self._device_token_retry_budget_used = False
        self._pending_startup_reconnect_delay_ms = None
        self._pending_connect_error_detail_code = None
        self._pending_connect_error_details = None
        self._clear_reconnect_timer()

        if self._tick_timer:
            self._tick_timer.cancel()
            self._tick_timer = None

        self._clear_connect_challenge_timeout()

        if self._pending_stop:
            self._flush_pending_errors(Exception("gateway client stopped"))
            return self._pending_stop["promise"]

        ws = self._ws
        self._ws = None

        if ws:
            loop = asyncio.get_running_loop()
            promise = loop.create_future()
            self._pending_stop = {
                "ws": ws,
                "promise": promise,
            }

            async def _force_terminate():
                await asyncio.sleep(_FORCE_STOP_TERMINATE_GRACE_MS / 1000.0)
                try:
                    if hasattr(ws, 'close'):
                        await ws.close(code=1000, reason="force terminate")
                except Exception:
                    pass
                self._resolve_pending_stop()

            force_task = asyncio.create_task(_force_terminate)
            self._pending_stop["terminateTimer"] = force_task

            try:
                await ws.close(code=1000, reason="client stopped")
            except Exception:
                pass

            self._flush_pending_errors(Exception("gateway client stopped"))
            return promise

        self._flush_pending_errors(Exception("gateway client stopped"))
        return None

    def _resolve_pending_stop(self) -> None:
        if not self._pending_stop:
            return
        pending = self._pending_stop
        terminate_timer = pending.get("terminateTimer")
        if terminate_timer:
            terminate_timer.cancel()
        self._pending_stop = None
        promise = pending.get("promise")
        if promise and not promise.done():
            promise.set_result(None)

    def _send_connect(self) -> None:
        if self._connect_sent:
            return

        nonce = self._normalize_optional_string(self._connect_nonce) or ""
        if not nonce:
            self._notify_connect_error(
                Exception("gateway connect challenge missing nonce")
            )
            if self._ws:
                try:
                    asyncio.create_task(self._ws.close(code=1008, reason="connect challenge missing nonce"))
                except Exception:
                    pass
            return

        role = self._options.role or "operator"

        try:
            assembled = self._assemble_connect_params(role=role, nonce=nonce)
        except Exception as err:
            self._handle_connect_failure(err)
            return

        self._connect_sent = True
        self._clear_connect_challenge_timeout()

        async def _do_connect():
            try:
                hello_ok = await self._request_raw("connect", assembled["params"])
                self._hello_ok_received = True
                self._pending_device_token_retry = False
                self._device_token_retry_budget_used = False
                self._pending_startup_reconnect_delay_ms = None
                self._pending_connect_error_detail_code = None
                self._pending_connect_error_details = None
                self._suppressed_transient_pre_hello_clean_closes = 0

                if isinstance(hello_ok, dict):
                    auth_info = hello_ok.get("auth")
                    if auth_info and auth_info.get("deviceToken") and self._options.device_identity:
                        self._deps.store_device_auth_token({
                            "deviceId": self._options.device_identity.device_id,
                            "role": auth_info.get("role") or role,
                            "token": auth_info.get("deviceToken"),
                            "scopes": auth_info.get("scopes") or [],
                            "env": self._options.env,
                        })

                self._backoff_ms = 1000
                policy = hello_ok.get("policy") if isinstance(hello_ok, dict) else None
                if policy and isinstance(policy.get("tickIntervalMs"), int):
                    self._tick_interval_ms = policy["tickIntervalMs"]
                else:
                    self._tick_interval_ms = 30_000

                self._last_tick = time.monotonic() * 1000
                self._start_tick_watch()
                self._notify_hello_ok(hello_ok)
            except GatewayClientTransientPreHelloCloseError:
                pass
            except GatewayClientRequestError as err:
                self._pending_connect_error_detail_code = read_connect_error_detail_code(err.details)
                self._pending_connect_error_details = err.details

                should_retry_with_device_token = self._should_retry_with_stored_device_token({
                    "error": err,
                    "explicitGatewayToken": self._normalize_optional_string(self._options.token),
                    "resolvedDeviceToken": assembled.get("resolvedDeviceToken"),
                    "storedToken": assembled.get("storedToken"),
                })

                if (
                    self._options.device_identity
                    and assembled.get("usingStoredDeviceToken")
                    and read_connect_error_detail_code(err.details) == "AUTH_DEVICE_TOKEN_MISMATCH"
                ):
                    device_id = self._options.device_identity.device_id
                    try:
                        self._deps.clear_device_auth_token({
                            "deviceId": device_id,
                            "role": role,
                            "env": self._options.env,
                        })
                        self._log_debug(f"cleared stale device-auth token for device {device_id}")
                    except Exception as clear_err:
                        self._log_debug(
                            f"failed clearing stale device-auth token for device {device_id}: {str(clear_err)}"
                        )

                if should_retry_with_device_token:
                    self._pending_device_token_retry = True
                    self._device_token_retry_budget_used = True
                    self._backoff_ms = min(self._backoff_ms, 250)

                startup_retry_after = resolve_gateway_startup_retry_after_ms(err)
                if startup_retry_after is not None:
                    self._pending_startup_reconnect_delay_ms = startup_retry_after
                    self._log_debug(f"gateway connect failed: {self._format_gateway_client_error_for_log(err)}")
                    if self._ws:
                        try:
                            asyncio.create_task(self._ws.close(code=1013, reason="gateway starting"))
                        except Exception:
                            pass
                    return

                if self._should_retry_without_approval_runtime_token({
                    "error": err,
                    "authApprovalRuntimeToken": assembled.get("authApprovalRuntimeToken"),
                }):
                    self._approval_runtime_token_compatibility_disabled = True
                    self._approval_runtime_token_retry_budget_used = True
                    self._backoff_ms = min(self._backoff_ms, 250)
                    self._log_debug("gateway rejected approval runtime auth field; retrying without it")
                    if self._ws:
                        try:
                            asyncio.create_task(self._ws.close(code=1008, reason="connect retry"))
                        except Exception:
                            pass
                    return

                self._notify_connect_error(err)
                msg = f"gateway connect failed: {self._format_gateway_client_error_for_log(err)}"
                if self._options.mode == "probe" or self._is_gateway_client_stopped_error(err):
                    self._log_debug(msg)
                else:
                    self._log_error(msg)
                if self._ws:
                    try:
                        asyncio.create_task(self._ws.close(code=1008, reason="connect failed"))
                    except Exception:
                        pass
            except Exception as err:
                self._notify_connect_error(err if isinstance(err, Exception) else Exception(str(err)))
                msg = f"gateway connect failed: {self._format_gateway_client_error_for_log(err)}"
                if self._options.mode == "probe" or self._is_gateway_client_stopped_error(err):
                    self._log_debug(msg)
                else:
                    self._log_error(msg)
                if self._ws:
                    try:
                        asyncio.create_task(self._ws.close(code=1008, reason="connect failed"))
                    except Exception:
                        pass

        asyncio.create_task(_do_connect())

    def _assemble_connect_params(self, *, role: str, nonce: str) -> dict:
        selected_auth = self._select_connect_auth(role)

        auth_token = selected_auth.get("authToken")
        auth_bootstrap_token = selected_auth.get("authBootstrapToken")
        auth_device_token = selected_auth.get("authDeviceToken")
        auth_password = selected_auth.get("authPassword")
        auth_approval_runtime_token = selected_auth.get("authApprovalRuntimeToken")
        signature_token = selected_auth.get("signatureToken")
        resolved_device_token = selected_auth.get("resolvedDeviceToken")
        stored_token = selected_auth.get("storedToken")
        stored_scopes = selected_auth.get("storedScopes")
        using_stored_device_token = selected_auth.get("usingStoredDeviceToken")

        if self._pending_device_token_retry and auth_device_token:
            self._pending_device_token_retry = False

        auth = None
        if auth_token or auth_bootstrap_token or auth_password or resolved_device_token or auth_approval_runtime_token:
            auth = {
                "token": auth_token,
                "bootstrapToken": auth_bootstrap_token,
                "deviceToken": auth_device_token or resolved_device_token,
                "password": auth_password,
                "approvalRuntimeToken": auth_approval_runtime_token,
            }

        signed_at_ms = int(time.time.monotonic() * 1000)
        scopes = self._resolve_connect_scopes(
            using_stored_device_token=using_stored_device_token,
            stored_scopes=stored_scopes,
        )
        platform = self._options.platform or os.name

        params = {
            "minProtocol": self._options.min_protocol or MIN_CLIENT_PROTOCOL_VERSION,
            "maxProtocol": self._options.max_protocol or PROTOCOL_VERSION,
            "client": {
                "id": self._options.client_name or "openclaw-gateway",
                "displayName": self._options.client_display_name,
                "version": self._options.client_version or _DEFAULT_CLIENT_VERSION,
                "platform": platform,
                "deviceFamily": self._options.device_family,
                "mode": self._options.mode or "backend",
                "instanceId": self._options.instance_id,
            },
            "caps": self._options.caps if isinstance(self._options.caps, list) else [],
            "commands": self._options.commands if isinstance(self._options.commands, list) else None,
            "permissions": (
                self._options.permissions
                if isinstance(self._options.permissions, dict)
                else None
            ),
            "pathEnv": self._options.path_env,
            "auth": auth,
            "role": role,
            "scopes": scopes,
            "device": self._build_device_connect_params({
                "nonce": nonce,
                "role": role,
                "scopes": scopes,
                "signatureToken": signature_token,
                "signedAtMs": signed_at_ms,
                "platform": platform,
            }),
        }

        return {
            "params": params,
            "authApprovalRuntimeToken": auth_approval_runtime_token,
            "resolvedDeviceToken": resolved_device_token,
            "storedToken": stored_token,
            "usingStoredDeviceToken": using_stored_device_token,
        }

    def _build_device_connect_params(self, params: dict) -> Optional[dict]:
        if not self._options.device_identity:
            return None

        nonce = params["nonce"]
        role = params["role"]
        scopes = params["scopes"]
        signature_token = params.get("signatureToken")
        signed_at_ms = params["signedAtMs"]
        platform = params["platform"]

        payload = build_device_auth_payload_v3(
            device_id=self._options.device_identity.device_id,
            client_id=self._options.client_name or "openclaw-gateway",
            client_mode=self._options.mode or "backend",
            role=role,
            scopes=scopes,
            signed_at_ms=signed_at_ms,
            token=signature_token,
            nonce=nonce,
            platform=platform,
            device_family=self._options.device_family,
        )

        signature = self._deps.sign_device_payload(
            self._options.device_identity.private_key_pem, payload
        )

        return {
            "id": self._options.device_identity.device_id,
            "publicKey": self._deps.public_key_raw_base64url_from_pem(
                self._options.device_identity.public_key_pem
            ),
            "signature": signature,
            "signedAt": signed_at_ms,
            "nonce": nonce,
        }

    def _handle_connect_failure(self, err: Exception) -> None:
        self._clear_connect_challenge_timeout()
        self._closed = True
        self._notify_connect_error(err)
        msg = f"gateway connect failed: {self._format_gateway_client_error_for_log(err)}"
        if self._options.mode == "probe" or self._is_gateway_client_stopped_error(err):
            self._log_debug(msg)
        else:
            self._log_error(msg)
        if self._ws:
            try:
                asyncio.create_task(self._ws.close(code=1008, reason="connect failed"))
            except Exception:
                pass

    def _resolve_connect_scopes(
        self,
        *,
        using_stored_device_token: Optional[bool] = None,
        stored_scopes: Optional[list[str]] = None,
    ) -> list[str]:
        if isinstance(self._options.scopes, list):
            return self._options.scopes
        if using_stored_device_token and isinstance(stored_scopes, list) and len(stored_scopes) > 0:
            return stored_scopes
        return self._options.scopes or ["operator.admin"]

    def _load_stored_device_auth(self, role: str) -> Optional[dict]:
        if not self._options.device_identity:
            return None
        stored_auth = self._deps.load_device_auth_token({
            "deviceId": self._options.device_identity.device_id,
            "role": role,
            "env": self._options.env,
        })
        if not stored_auth:
            return None
        token = stored_auth.token if hasattr(stored_auth, 'token') else stored_auth.get("token")
        scopes = stored_auth.scopes if hasattr(stored_auth, 'scopes') else stored_auth.get("scopes")
        return {"token": token, "scopes": scopes}

    def _should_pause_reconnect_after_auth_failure(
        self,
        *,
        detail_code: Optional[str],
        details: Any,
    ) -> bool:
        if not detail_code:
            return False

        pairing_details = read_pairing_connect_error_details(details)
        if (
            detail_code == "PAIRING_REQUIRED"
            and pairing_details is not None
            and (
                pairing_details.get("pauseReconnect") is False
                or pairing_details.get("recommendedNextStep") == "wait_then_retry"
            )
        ):
            return False

        pause_codes = {
            "AUTH_TOKEN_MISSING",
            "AUTH_BOOTSTRAP_TOKEN_INVALID",
            "AUTH_PASSWORD_MISSING",
            "AUTH_PASSWORD_MISMATCH",
            "AUTH_RATE_LIMITED",
            "AUTH_DEVICE_TOKEN_MISMATCH",
            "AUTH_SCOPE_MISMATCH",
            "PAIRING_REQUIRED",
            "CONTROL_UI_DEVICE_IDENTITY_REQUIRED",
            "DEVICE_IDENTITY_REQUIRED",
            "CLIENT_VERSION_MISMATCH",
        }
        if detail_code in pause_codes:
            return True

        if detail_code == "AUTH_TOKEN_MISMATCH":
            return not self._pending_device_token_retry

        return False

    def _should_retry_with_stored_device_token(
        self,
        *,
        error: Any,
        explicit_gateway_token: Optional[str],
        stored_token: Optional[str],
        resolved_device_token: Optional[str],
    ) -> bool:
        if self._device_token_retry_budget_used:
            return False
        if resolved_device_token:
            return False
        if not explicit_gateway_token or not stored_token:
            return False
        if not self._is_trusted_device_retry_endpoint():
            return False
        if not isinstance(error, GatewayClientRequestError):
            return False
        detail_code = read_connect_error_detail_code(error.details)
        advice = read_connect_error_recovery_advice(error.details)
        retry_with_device_token_recommended = advice.get("recommendedNextStep") == "retry_with_device_token"
        return (
            advice.get("canRetryWithDeviceToken") is True
            or retry_with_device_token_recommended
            or detail_code == "AUTH_TOKEN_MISMATCH"
        )

    def _should_retry_without_approval_runtime_token(
        self,
        *,
        error: Any,
        auth_approval_runtime_token: Optional[str],
    ) -> bool:
        if self._approval_runtime_token_retry_budget_used:
            return False
        if not auth_approval_runtime_token:
            return False
        if not isinstance(error, GatewayClientRequestError):
            return False
        if error.gateway_code != "INVALID_REQUEST":
            return False
        message = str(error).lower()
        return "invalid connect params" in message and "approvalruntimetoken" in message

    def _is_trusted_device_retry_endpoint(self) -> bool:
        raw_url = self._options.url or _DEFAULT_GATEWAY_CLIENT_URL
        try:
            from urllib.parse import urlparse
            parsed = urlparse(raw_url)
            protocol = parsed.scheme
            if protocol == "https":
                protocol = "wss"
            elif protocol == "http":
                protocol = "ws"
            if self._is_loopback_host(parsed.hostname or ""):
                return True
            return protocol == "wss" and bool((self._options.tls_fingerprint or "").strip())
        except Exception:
            return False

    def _select_connect_auth(self, role: str) -> dict:
        explicit_gateway_token = self._normalize_optional_string(self._options.token)
        explicit_bootstrap_token = self._normalize_optional_string(self._options.bootstrap_token)
        explicit_device_token = self._normalize_optional_string(self._options.device_token)
        auth_password = self._normalize_optional_string(self._options.password)
        auth_approval_runtime_token = (
            None
            if self._approval_runtime_token_compatibility_disabled
            else self._normalize_optional_string(self._options.approval_runtime_token)
        )

        stored_auth = self._load_stored_device_auth(role)
        stored_token = stored_auth.get("token") if stored_auth else None
        stored_scopes = stored_auth.get("scopes") if stored_auth else None

        should_use_device_retry_token = (
            self._pending_device_token_retry
            and not explicit_device_token
            and bool(explicit_gateway_token)
            and bool(stored_token)
            and self._is_trusted_device_retry_endpoint()
        )

        if explicit_device_token is not None:
            resolved_device_token = explicit_device_token
        elif should_use_device_retry_token or (
            not explicit_gateway_token
            and not auth_password
            and (not explicit_bootstrap_token or bool(stored_token))
        ):
            resolved_device_token = stored_token
        else:
            resolved_device_token = None

        reusing_stored_device_token = (
            bool(resolved_device_token)
            and not explicit_device_token
            and bool(stored_token)
            and resolved_device_token == stored_token
        )

        auth_token = explicit_gateway_token or resolved_device_token
        if explicit_gateway_token or resolved_device_token or auth_password:
            auth_bootstrap_token = None
        else:
            auth_bootstrap_token = explicit_bootstrap_token

        return {
            "authToken": auth_token,
            "authBootstrapToken": auth_bootstrap_token,
            "authDeviceToken": stored_token if should_use_device_retry_token else None,
            "authPassword": auth_password,
            "authApprovalRuntimeToken": auth_approval_runtime_token,
            "signatureToken": auth_token or auth_bootstrap_token,
            "resolvedDeviceToken": resolved_device_token,
            "storedToken": stored_token,
            "storedScopes": stored_scopes,
            "usingStoredDeviceToken": reusing_stored_device_token,
        }

    def _handle_message(self, raw: str) -> None:
        try:
            parsed = json.loads(raw)
        except Exception as err:
            self._log_debug(f"gateway client parse error: {self._format_gateway_client_error_for_log(err)}")
            return

        if self._is_gateway_event_frame(parsed):
            self._last_tick = time.monotonic() * 1000
            evt = parsed
            event_name = evt.get("event")

            if event_name == "connect.challenge":
                payload = evt.get("payload") or {}
                nonce = None
                if isinstance(payload, dict):
                    nonce = payload.get("nonce")
                if not nonce or not isinstance(nonce, str) or not nonce.strip():
                    self._notify_connect_error(
                        Exception("gateway connect challenge missing nonce")
                    )
                    if self._ws:
                        try:
                            asyncio.create_task(self._ws.close(code=1008, reason="connect challenge missing nonce"))
                        except Exception:
                            pass
                    return
                self._connect_nonce = nonce.strip()
                if self._socket_opened:
                    self._send_connect()
                return

            try:
                seq = evt.get("seq")
                if isinstance(seq, int):
                    if self._last_seq is not None and seq > self._last_seq + 1:
                        gap_handler = self._options.on_gap
                        if gap_handler:
                            try:
                                gap_handler({"expected": self._last_seq + 1, "received": seq})
                            except Exception:
                                pass
                    self._last_seq = seq

                if event_name == "tick":
                    self._last_tick = time.monotonic() * 1000

                handler = self._options.on_event
                if handler:
                    handler(evt)
            except Exception as err:
                self._log_debug(
                    f"gateway client event handler error: {self._format_gateway_client_error_for_log(err)}"
                )
            return

        if self._is_gateway_response_frame(parsed):
            self._last_tick = time.monotonic() * 1000
            pending = self._pending.get(parsed.get("id", ""))
            if not pending:
                return

            payload = parsed.get("payload") or {}
            status = payload.get("status") if isinstance(payload, dict) else None

            if pending.get("expectFinal") and status == "accepted":
                if not pending.get("acceptedNotified"):
                    pending["acceptedNotified"] = True
                    on_accepted = pending.get("onAccepted")
                    if on_accepted:
                        try:
                            on_accepted(parsed.get("payload"))
                        except Exception as err:
                            self._log_debug(
                                f"gateway client accepted callback error: {self._format_gateway_client_error_for_log(err)}"
                            )
                return

            del self._pending[parsed.get("id", "")]
            cleanup_fn = pending.get("cleanup")
            if cleanup_fn:
                cleanup_fn()

            if parsed.get("ok"):
                resolve_fn = pending.get("resolve")
                if resolve_fn:
                    resolve_fn(parsed.get("payload"))
            else:
                reject_fn = pending.get("reject")
                if reject_fn:
                    error_data = parsed.get("error")
                    if not isinstance(error_data, dict):
                        error_data = {}
                    reject_fn(GatewayClientRequestError({
                        "code": error_data.get("code"),
                        "message": error_data.get("message", "unknown error"),
                        "details": error_data.get("details"),
                        "retryable": error_data.get("retryable"),
                        "retryAfterMs": error_data.get("retryAfterMs"),
                    }))

    def _begin_preauth_handshake(self) -> None:
        if self._connect_sent:
            return
        if self._connect_nonce and not self._connect_sent:
            self._arm_connect_challenge_timeout()
            self._send_connect()
            return
        self._arm_connect_challenge_timeout()

    def _clear_connect_challenge_timeout(self) -> None:
        if self._connect_timer:
            self._connect_timer.cancel()
            self._connect_timer = None

    def _clear_reconnect_timer(self) -> None:
        if self._reconnect_timer:
            self._reconnect_timer.cancel()
            self._reconnect_timer = None

    def _arm_connect_challenge_timeout(self) -> None:
        timeout_ms = self._resolve_gateway_client_connect_challenge_timeout_ms()
        armed_at = time.monotonic() * 1000
        self._clear_connect_challenge_timeout()

        async def _timeout_task():
            await asyncio.sleep(timeout_ms / 1000.0)
            if self._connect_sent or not self._ws:
                return
            elapsed_ms = int(time.monotonic() * 1000 - armed_at)
            self._notify_connect_error(
                Exception(
                    f"gateway connect challenge timeout (waited {elapsed_ms}ms, limit {timeout_ms}ms)"
                )
            )
            if self._ws:
                try:
                    await self._ws.close(code=1008, reason="connect challenge timeout")
                except Exception:
                    pass

        self._connect_timer = asyncio.create_task(_timeout_task())

    def _schedule_reconnect(self) -> None:
        if self._closed:
            return

        if self._tick_timer:
            self._tick_timer.cancel()
            self._tick_timer = None

        self._clear_reconnect_timer()

        startup_delay = self._pending_startup_reconnect_delay_ms
        self._pending_startup_reconnect_delay_ms = None
        delay = startup_delay if startup_delay is not None else self._backoff_ms

        if startup_delay is None:
            self._backoff_ms = min(self._backoff_ms * 2, 30_000)

        async def _reconnect_task():
            await asyncio.sleep(delay / 1000.0)
            self._reconnect_timer = None
            await self.start()

        self._reconnect_timer = asyncio.create_task(_reconnect_task())

    def _flush_pending_errors(self, err: Exception) -> None:
        for key in list(self._pending.keys()):
            p = self._pending[key]
            cleanup_fn = p.get("cleanup")
            if cleanup_fn:
                cleanup_fn()
            reject_fn = p.get("reject")
            if reject_fn:
                reject_fn(err)
        self._pending.clear()

    def _start_tick_watch(self) -> None:
        if self._tick_timer:
            self._tick_timer.cancel()

        raw_min_interval = self._options.tick_watch_min_interval_ms
        if raw_min_interval is not None and raw_min_interval == int(raw_min_interval) and raw_min_interval == raw_min_interval:
            min_interval = max(1, min(30_000, int(raw_min_interval)))
        else:
            min_interval = 1000

        interval = resolve_safe_timeout_delay_ms(max(self._tick_interval_ms, min_interval))

        async def _tick_task():
            while not self._closed:
                await asyncio.sleep(interval / 1000.0)
                if self._closed:
                    return
                if self._last_tick is None:
                    continue
                if len(self._pending) > 0:
                    continue
                gap = time.monotonic() * 1000 - self._last_tick
                raw_timeout_ms = self._options.tick_watch_timeout_ms
                if raw_timeout_ms is not None and raw_timeout_ms == int(raw_timeout_ms) and raw_timeout_ms == raw_timeout_ms:
                    timeout_ms = max(1, int(raw_timeout_ms))
                else:
                    timeout_ms = self._tick_interval_ms * 2
                if gap > timeout_ms:
                    if self._ws:
                        try:
                            await self._ws.close(code=4000, reason="tick timeout")
                        except Exception:
                            pass
                    return

        self._tick_timer = asyncio.create_task(_tick_task())

    async def _request_raw(self, method: str, params: Any = None) -> Any:
        ws = self._ws
        if not ws:
            raise Exception("gateway not connected")

        request_id = str(uuid.uuid4())
        frame = {"type": "req", "id": request_id, "method": method, "params": params}
        frame_error = self._validate_client_request_frame(frame)
        if frame_error:
            raise Exception(f"invalid request frame: {frame_error}")

        loop = asyncio.get_running_loop()
        resolve_future = loop.create_future()
        reject_future = loop.create_future()
        done_future = loop.create_future()

        async def _on_done():
            resolve_future.add_done_callback(lambda _f: done_future.set_result(None) if not done_future.done() else None)
            reject_future.add_done_callback(lambda _f: done_future.set_result(None) if not done_future.done() else None)

        _on_done()

        pending_entry = {
            "resolve": lambda v: resolve_future.set_result(v) if not resolve_future.done() else None,
            "reject": lambda e: reject_future.set_exception(e) if not reject_future.done() else None,
            "expectFinal": False,
            "timeout": None,
            "onAccepted": None,
            "acceptedNotified": False,
            "cleanup": None,
        }

        self._pending[request_id] = pending_entry

        try:
            await ws.send(json.dumps(frame))
        except Exception as err:
            del self._pending[request_id]
            raise err

        try:
            await done_future
        except Exception:
            raise

        if resolve_future.done():
            return resolve_future.result()
        if reject_future.done():
            raise reject_future.exception() or Exception("gateway request failed")
        raise Exception("gateway request failed")

    async def request(
        self,
        method: str,
        params: Any = None,
        options: Optional[GatewayClientRequestOptions] = None,
    ) -> Any:
        ws = self._ws
        if not ws:
            raise Exception("gateway not connected")

        abort_event = options.abort_event if options else None
        if abort_event and abort_event.is_set():
            raise self._create_gateway_request_abort_error(method)

        request_id = str(uuid.uuid4())
        frame = {"type": "req", "id": request_id, "method": method, "params": params}
        frame_error = self._validate_client_request_frame(frame)
        if frame_error:
            raise Exception(f"invalid request frame: {frame_error}")

        expect_final = options.expect_final if options and options.expect_final is not None else False

        timeout_ms = None
        if options and options.timeout_ms is not None:
            if options.timeout_ms == int(options.timeout_ms):
                timeout_ms = resolve_safe_timeout_delay_ms(int(options.timeout_ms), min_ms=0)
        elif expect_final:
            timeout_ms = None
        else:
            timeout_ms = self._request_timeout_ms

        loop = asyncio.get_running_loop()
        resolve_future = loop.create_future()
        reject_future = loop.create_future()

        pending_entry: dict[str, Any] = {
            "resolve": lambda v: resolve_future.set_result(v) if not resolve_future.done() else None,
            "reject": lambda e: reject_future.set_exception(e) if not reject_future.done() else None,
            "expectFinal": expect_final,
            "timeout": None,
            "onAccepted": options.on_accepted if options else None,
            "acceptedNotified": False,
            "cleanup": None,
        }

        if timeout_ms is not None:
            async def _timeout_handler():
                await asyncio.sleep(timeout_ms / 1000.0)
                if request_id in self._pending:
                    del self._pending[request_id]
                    cleanup_fn = pending_entry.get("cleanup")
                    if cleanup_fn:
                        cleanup_fn()
                    if not reject_future.done():
                        reject_future.set_result(Exception(f"gateway request timeout for {method}"))

            pending_entry["timeout"] = asyncio.create_task(_timeout_handler)

        def _cleanup():
            timeout_task = pending_entry.get("timeout")
            if timeout_task:
                timeout_task.cancel()
            if abort_event:
                try:
                    abort_event.remove_listener(_on_abort)
                except (ValueError, AttributeError):
                    pass

        def _on_abort():
            if request_id in self._pending:
                del self._pending[request_id]
                cleanup_fn = pending_entry.get("cleanup")
                if cleanup_fn:
                    cleanup_fn()
                if not reject_future.done():
                    reject_future.set_result(self._create_gateway_request_abort_error(method))

        pending_entry["cleanup"] = _cleanup

        if abort_event:
            abort_event.add_listener(_on_abort)

        self._pending[request_id] = pending_entry

        try:
            await ws.send(json.dumps(frame))
        except Exception as err:
            del self._pending[request_id]
            cleanup_fn = pending_entry.get("cleanup")
            if cleanup_fn:
                cleanup_fn()
            raise err

        try:
            done, pending = await asyncio.wait(
                [resolve_future, reject_future],
                return_when=asyncio.FIRST_COMPLETED,
            )
            if resolve_future in done:
                return resolve_future.result()
            if reject_future in done:
                exc = reject_future.exception()
                if exc:
                    raise exc
                raise Exception(f"gateway request failed for {method}")
            for task in pending:
                task.cancel()
            raise Exception(f"gateway request failed for {method}")
        except asyncio.CancelledError:
            raise self._create_gateway_request_abort_error(method)

    @staticmethod
    def _create_gateway_request_abort_error(method: str) -> Exception:
        err = Exception(f"gateway request aborted for {method}")
        err.name = "AbortError"
        return err
