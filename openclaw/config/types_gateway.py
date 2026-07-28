from __future__ import annotations

from typing import Any, Literal, Optional, List, Dict

from pydantic import BaseModel, Field


GatewayBindMode = Literal["auto", "lan", "loopback", "custom", "tailnet"]
GatewayAuthMode = Literal["none", "token", "password", "trusted-proxy"]
GatewayTailscaleMode = Literal["off", "serve", "funnel"]
GatewayReloadMode = Literal["off", "restart", "hot", "hybrid"]


class GatewayTlsConfig(BaseModel):
    enabled: Optional[bool] = None
    auto_generate: Optional[bool] = Field(default=None, alias="autoGenerate")
    cert_path: Optional[str] = Field(default=None, alias="certPath")
    key_path: Optional[str] = Field(default=None, alias="keyPath")
    ca_path: Optional[str] = Field(default=None, alias="caPath")

    model_config = {"populate_by_name": True}


class WideAreaDiscoveryConfig(BaseModel):
    enabled: Optional[bool] = None
    domain: Optional[str] = None


MdnsDiscoveryMode = Literal["off", "minimal", "full"]


class MdnsDiscoveryConfig(BaseModel):
    mode: Optional[MdnsDiscoveryMode] = None


class DiscoveryConfig(BaseModel):
    wide_area: Optional[WideAreaDiscoveryConfig] = Field(default=None, alias="wideArea")
    mdns: Optional[MdnsDiscoveryConfig] = None


class TalkProviderConfig(BaseModel):
    api_key: Optional[str] = Field(default=None, alias="apiKey")

    model_config = {"populate_by_name": True, "extra": "allow"}


class TalkRealtimeConfig(BaseModel):
    provider: Optional[str] = None
    providers: Optional[Dict[str, TalkProviderConfig]] = None
    model: Optional[str] = None
    speaker_voice: Optional[str] = Field(default=None, alias="speakerVoice")
    speaker_voice_id: Optional[str] = Field(default=None, alias="speakerVoiceId")
    voice: Optional[str] = None
    instructions: Optional[str] = None
    mode: Optional[str] = None
    transport: Optional[str] = None
    brain: Optional[str] = None
    consult_routing: Optional[str] = Field(default=None, alias="consultRouting")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ResolvedTalkConfig(BaseModel):
    provider: str
    config: TalkProviderConfig


class TalkConfig(BaseModel):
    provider: Optional[str] = None
    providers: Optional[Dict[str, TalkProviderConfig]] = None
    realtime: Optional[TalkRealtimeConfig] = None
    consult_thinking_level: Optional[str] = Field(default=None, alias="consultThinkingLevel")
    consult_fast_mode: Optional[bool] = Field(default=None, alias="consultFastMode")
    speech_locale: Optional[str] = Field(default=None, alias="speechLocale")
    interrupt_on_speech: Optional[bool] = Field(default=None, alias="interruptOnSpeech")
    silence_timeout_ms: Optional[int] = Field(default=None, alias="silenceTimeoutMs")

    model_config = {"populate_by_name": True, "extra": "allow"}


class GatewayControlUiConfig(BaseModel):
    enabled: Optional[bool] = None
    base_path: Optional[str] = Field(default=None, alias="basePath")
    root: Optional[str] = None
    embed_sandbox: Optional[str] = Field(default=None, alias="embedSandbox")
    allow_external_embed_urls: Optional[bool] = Field(default=None, alias="allowExternalEmbedUrls")
    chat_message_max_width: Optional[str] = Field(default=None, alias="chatMessageMaxWidth")
    allowed_origins: Optional[List[str]] = Field(default=None, alias="allowedOrigins")
    dangerously_allow_host_header_origin_fallback: Optional[bool] = Field(
        default=None, alias="dangerouslyAllowHostHeaderOriginFallback"
    )
    allow_insecure_auth: Optional[bool] = Field(default=None, alias="allowInsecureAuth")
    dangerously_disable_device_auth: Optional[bool] = Field(
        default=None, alias="dangerouslyDisableDeviceAuth"
    )

    model_config = {"populate_by_name": True}


class GatewayTrustedProxyConfig(BaseModel):
    user_header: str = Field(alias="userHeader")
    required_headers: Optional[List[str]] = Field(default=None, alias="requiredHeaders")
    allow_users: Optional[List[str]] = Field(default=None, alias="allowUsers")
    allow_loopback: Optional[bool] = Field(default=None, alias="allowLoopback")

    model_config = {"populate_by_name": True}


class GatewayAuthRateLimitConfig(BaseModel):
    max_attempts: Optional[int] = Field(default=None, alias="maxAttempts")
    window_ms: Optional[int] = Field(default=None, alias="windowMs")
    lockout_ms: Optional[int] = Field(default=None, alias="lockoutMs")
    exempt_loopback: Optional[bool] = Field(default=None, alias="exemptLoopback")

    model_config = {"populate_by_name": True}


class GatewayAuthConfig(BaseModel):
    mode: Optional[GatewayAuthMode] = None
    token: Optional[str] = None
    password: Optional[str] = None
    allow_tailscale: Optional[bool] = Field(default=None, alias="allowTailscale")
    rate_limit: Optional[GatewayAuthRateLimitConfig] = Field(default=None, alias="rateLimit")
    trusted_proxy: Optional[GatewayTrustedProxyConfig] = Field(default=None, alias="trustedProxy")

    model_config = {"populate_by_name": True}


class GatewayTailscaleConfig(BaseModel):
    mode: Optional[GatewayTailscaleMode] = None
    reset_on_exit: Optional[bool] = Field(default=None, alias="resetOnExit")
    service_name: Optional[str] = Field(default=None, alias="serviceName")
    preserve_funnel: Optional[bool] = Field(default=None, alias="preserveFunnel")

    model_config = {"populate_by_name": True}


class GatewayRemoteConfig(BaseModel):
    enabled: Optional[bool] = None
    url: Optional[str] = None
    transport: Optional[str] = None
    remote_port: Optional[int] = Field(default=None, alias="remotePort")
    token: Optional[str] = None
    password: Optional[str] = None
    tls_fingerprint: Optional[str] = Field(default=None, alias="tlsFingerprint")
    ssh_target: Optional[str] = Field(default=None, alias="sshTarget")
    ssh_identity: Optional[str] = Field(default=None, alias="sshIdentity")

    model_config = {"populate_by_name": True}


class GatewayReloadConfig(BaseModel):
    mode: Optional[GatewayReloadMode] = None
    debounce_ms: Optional[int] = Field(default=None, alias="debounceMs")
    deferral_timeout_ms: Optional[int] = Field(default=None, alias="deferralTimeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpChatCompletionsImagesConfig(BaseModel):
    allow_url: Optional[bool] = Field(default=None, alias="allowUrl")
    url_allowlist: Optional[List[str]] = Field(default=None, alias="urlAllowlist")
    allowed_mimes: Optional[List[str]] = Field(default=None, alias="allowedMimes")
    max_bytes: Optional[int] = Field(default=None, alias="maxBytes")
    max_redirects: Optional[int] = Field(default=None, alias="maxRedirects")
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpChatCompletionsConfig(BaseModel):
    enabled: Optional[bool] = None
    max_body_bytes: Optional[int] = Field(default=None, alias="maxBodyBytes")
    max_image_parts: Optional[int] = Field(default=None, alias="maxImageParts")
    max_total_image_bytes: Optional[int] = Field(default=None, alias="maxTotalImageBytes")
    images: Optional[GatewayHttpChatCompletionsImagesConfig] = None

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesFilesConfig(BaseModel):
    allow_url: Optional[bool] = Field(default=None, alias="allowUrl")
    url_allowlist: Optional[List[str]] = Field(default=None, alias="urlAllowlist")
    allowed_mimes: Optional[List[str]] = Field(default=None, alias="allowedMimes")
    max_bytes: Optional[int] = Field(default=None, alias="maxBytes")
    max_chars: Optional[int] = Field(default=None, alias="maxChars")
    max_redirects: Optional[int] = Field(default=None, alias="maxRedirects")
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesPdfConfig(BaseModel):
    max_pages: Optional[int] = Field(default=None, alias="maxPages")
    max_pixels: Optional[int] = Field(default=None, alias="maxPixels")
    min_text_chars: Optional[int] = Field(default=None, alias="minTextChars")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesImagesConfig(BaseModel):
    allow_url: Optional[bool] = Field(default=None, alias="allowUrl")
    url_allowlist: Optional[List[str]] = Field(default=None, alias="urlAllowlist")
    allowed_mimes: Optional[List[str]] = Field(default=None, alias="allowedMimes")
    max_bytes: Optional[int] = Field(default=None, alias="maxBytes")
    max_redirects: Optional[int] = Field(default=None, alias="maxRedirects")
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesConfig(BaseModel):
    enabled: Optional[bool] = None
    max_body_bytes: Optional[int] = Field(default=None, alias="maxBodyBytes")
    max_url_parts: Optional[int] = Field(default=None, alias="maxUrlParts")
    files: Optional[GatewayHttpResponsesFilesConfig] = None
    images: Optional[GatewayHttpResponsesImagesConfig] = None

    model_config = {"populate_by_name": True}


class GatewayHttpEndpointsConfig(BaseModel):
    chat_completions: Optional[GatewayHttpChatCompletionsConfig] = Field(
        default=None, alias="chatCompletions"
    )
    responses: Optional[GatewayHttpResponsesConfig] = None

    model_config = {"populate_by_name": True}


class GatewayHttpSecurityHeadersConfig(BaseModel):
    strict_transport_security: Optional[str | bool] = Field(
        default=None, alias="strictTransportSecurity"
    )

    model_config = {"populate_by_name": True}


class GatewayHttpConfig(BaseModel):
    endpoints: Optional[GatewayHttpEndpointsConfig] = None
    security_headers: Optional[GatewayHttpSecurityHeadersConfig] = Field(
        default=None, alias="securityHeaders"
    )

    model_config = {"populate_by_name": True}


class GatewayPushApnsRelayConfig(BaseModel):
    base_url: Optional[str] = Field(default=None, alias="baseUrl")
    timeout_ms: Optional[int] = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayPushApnsConfig(BaseModel):
    relay: Optional[GatewayPushApnsRelayConfig] = None


class GatewayPushConfig(BaseModel):
    apns: Optional[GatewayPushApnsConfig] = None


class GatewayNodePairingConfig(BaseModel):
    auto_approve_cidrs: Optional[List[str]] = Field(default=None, alias="autoApproveCidrs")

    model_config = {"populate_by_name": True}


class GatewayNodesConfig(BaseModel):
    browser: Optional[Dict[str, Any]] = None
    pairing: Optional[GatewayNodePairingConfig] = None
    allow_commands: Optional[List[str]] = Field(default=None, alias="allowCommands")
    deny_commands: Optional[List[str]] = Field(default=None, alias="denyCommands")

    model_config = {"populate_by_name": True}


class GatewayToolsConfig(BaseModel):
    deny: Optional[List[str]] = None
    allow: Optional[List[str]] = None


class GatewayConfig(BaseModel):
    port: Optional[int] = None
    mode: Optional[Literal["local", "remote"]] = None
    bind: Optional[GatewayBindMode] = None
    custom_bind_host: Optional[str] = Field(default=None, alias="customBindHost")
    control_ui: Optional[GatewayControlUiConfig] = Field(default=None, alias="controlUi")
    auth: Optional[GatewayAuthConfig] = None
    tailscale: Optional[GatewayTailscaleConfig] = None
    remote: Optional[GatewayRemoteConfig] = None
    reload: Optional[GatewayReloadConfig] = None
    tls: Optional[GatewayTlsConfig] = None
    http: Optional[GatewayHttpConfig] = None
    push: Optional[GatewayPushConfig] = None
    nodes: Optional[GatewayNodesConfig] = None
    trusted_proxies: Optional[List[str]] = Field(default=None, alias="trustedProxies")
    allow_real_ip_fallback: Optional[bool] = Field(default=None, alias="allowRealIpFallback")
    tools: Optional[GatewayToolsConfig] = None
    handshake_timeout_ms: Optional[int] = Field(default=None, alias="handshakeTimeoutMs")
    channel_health_check_minutes: Optional[int] = Field(
        default=None, alias="channelHealthCheckMinutes"
    )
    channel_stale_event_threshold_minutes: Optional[int] = Field(
        default=None, alias="channelStaleEventThresholdMinutes"
    )
    channel_max_restarts_per_hour: Optional[int] = Field(
        default=None, alias="channelMaxRestartsPerHour"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}
