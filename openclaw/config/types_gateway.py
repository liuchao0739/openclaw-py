from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


GatewayBindMode = Literal["auto", "lan", "loopback", "custom", "tailnet"]
GatewayAuthMode = Literal["none", "token", "password", "trusted-proxy"]
GatewayTailscaleMode = Literal["off", "serve", "funnel"]
GatewayReloadMode = Literal["off", "restart", "hot", "hybrid"]


class GatewayTlsConfig(BaseModel):
    enabled: bool | None = None
    auto_generate: bool | None = Field(default=None, alias="autoGenerate")
    cert_path: str | None = Field(default=None, alias="certPath")
    key_path: str | None = Field(default=None, alias="keyPath")
    ca_path: str | None = Field(default=None, alias="caPath")

    model_config = {"populate_by_name": True}


class WideAreaDiscoveryConfig(BaseModel):
    enabled: bool | None = None
    domain: str | None = None


MdnsDiscoveryMode = Literal["off", "minimal", "full"]


class MdnsDiscoveryConfig(BaseModel):
    mode: MdnsDiscoveryMode | None = None


class DiscoveryConfig(BaseModel):
    wide_area: WideAreaDiscoveryConfig | None = Field(default=None, alias="wideArea")
    mdns: MdnsDiscoveryConfig | None = None


class TalkProviderConfig(BaseModel):
    api_key: str | None = Field(default=None, alias="apiKey")

    model_config = {"populate_by_name": True, "extra": "allow"}


class TalkRealtimeConfig(BaseModel):
    provider: str | None = None
    providers: dict[str, TalkProviderConfig] | None = None
    model: str | None = None
    speaker_voice: str | None = Field(default=None, alias="speakerVoice")
    speaker_voice_id: str | None = Field(default=None, alias="speakerVoiceId")
    voice: str | None = None
    instructions: str | None = None
    mode: str | None = None
    transport: str | None = None
    brain: str | None = None
    consult_routing: str | None = Field(default=None, alias="consultRouting")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ResolvedTalkConfig(BaseModel):
    provider: str
    config: TalkProviderConfig


class TalkConfig(BaseModel):
    provider: str | None = None
    providers: dict[str, TalkProviderConfig] | None = None
    realtime: TalkRealtimeConfig | None = None
    consult_thinking_level: str | None = Field(default=None, alias="consultThinkingLevel")
    consult_fast_mode: bool | None = Field(default=None, alias="consultFastMode")
    speech_locale: str | None = Field(default=None, alias="speechLocale")
    interrupt_on_speech: bool | None = Field(default=None, alias="interruptOnSpeech")
    silence_timeout_ms: int | None = Field(default=None, alias="silenceTimeoutMs")

    model_config = {"populate_by_name": True, "extra": "allow"}


class GatewayControlUiConfig(BaseModel):
    enabled: bool | None = None
    base_path: str | None = Field(default=None, alias="basePath")
    root: str | None = None
    embed_sandbox: str | None = Field(default=None, alias="embedSandbox")
    allow_external_embed_urls: bool | None = Field(default=None, alias="allowExternalEmbedUrls")
    chat_message_max_width: str | None = Field(default=None, alias="chatMessageMaxWidth")
    allowed_origins: list[str] | None = Field(default=None, alias="allowedOrigins")
    dangerously_allow_host_header_origin_fallback: bool | None = Field(
        default=None, alias="dangerouslyAllowHostHeaderOriginFallback"
    )
    allow_insecure_auth: bool | None = Field(default=None, alias="allowInsecureAuth")
    dangerously_disable_device_auth: bool | None = Field(
        default=None, alias="dangerouslyDisableDeviceAuth"
    )

    model_config = {"populate_by_name": True}


class GatewayTrustedProxyConfig(BaseModel):
    user_header: str = Field(alias="userHeader")
    required_headers: list[str] | None = Field(default=None, alias="requiredHeaders")
    allow_users: list[str] | None = Field(default=None, alias="allowUsers")
    allow_loopback: bool | None = Field(default=None, alias="allowLoopback")

    model_config = {"populate_by_name": True}


class GatewayAuthRateLimitConfig(BaseModel):
    max_attempts: int | None = Field(default=None, alias="maxAttempts")
    window_ms: int | None = Field(default=None, alias="windowMs")
    lockout_ms: int | None = Field(default=None, alias="lockoutMs")
    exempt_loopback: bool | None = Field(default=None, alias="exemptLoopback")

    model_config = {"populate_by_name": True}


class GatewayAuthConfig(BaseModel):
    mode: GatewayAuthMode | None = None
    token: str | None = None
    password: str | None = None
    allow_tailscale: bool | None = Field(default=None, alias="allowTailscale")
    rate_limit: GatewayAuthRateLimitConfig | None = Field(default=None, alias="rateLimit")
    trusted_proxy: GatewayTrustedProxyConfig | None = Field(default=None, alias="trustedProxy")

    model_config = {"populate_by_name": True}


class GatewayTailscaleConfig(BaseModel):
    mode: GatewayTailscaleMode | None = None
    reset_on_exit: bool | None = Field(default=None, alias="resetOnExit")
    service_name: str | None = Field(default=None, alias="serviceName")
    preserve_funnel: bool | None = Field(default=None, alias="preserveFunnel")

    model_config = {"populate_by_name": True}


class GatewayRemoteConfig(BaseModel):
    enabled: bool | None = None
    url: str | None = None
    transport: str | None = None
    remote_port: int | None = Field(default=None, alias="remotePort")
    token: str | None = None
    password: str | None = None
    tls_fingerprint: str | None = Field(default=None, alias="tlsFingerprint")
    ssh_target: str | None = Field(default=None, alias="sshTarget")
    ssh_identity: str | None = Field(default=None, alias="sshIdentity")

    model_config = {"populate_by_name": True}


class GatewayReloadConfig(BaseModel):
    mode: GatewayReloadMode | None = None
    debounce_ms: int | None = Field(default=None, alias="debounceMs")
    deferral_timeout_ms: int | None = Field(default=None, alias="deferralTimeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpChatCompletionsImagesConfig(BaseModel):
    allow_url: bool | None = Field(default=None, alias="allowUrl")
    url_allowlist: list[str] | None = Field(default=None, alias="urlAllowlist")
    allowed_mimes: list[str] | None = Field(default=None, alias="allowedMimes")
    max_bytes: int | None = Field(default=None, alias="maxBytes")
    max_redirects: int | None = Field(default=None, alias="maxRedirects")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpChatCompletionsConfig(BaseModel):
    enabled: bool | None = None
    max_body_bytes: int | None = Field(default=None, alias="maxBodyBytes")
    max_image_parts: int | None = Field(default=None, alias="maxImageParts")
    max_total_image_bytes: int | None = Field(default=None, alias="maxTotalImageBytes")
    images: GatewayHttpChatCompletionsImagesConfig | None = None

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesFilesConfig(BaseModel):
    allow_url: bool | None = Field(default=None, alias="allowUrl")
    url_allowlist: list[str] | None = Field(default=None, alias="urlAllowlist")
    allowed_mimes: list[str] | None = Field(default=None, alias="allowedMimes")
    max_bytes: int | None = Field(default=None, alias="maxBytes")
    max_chars: int | None = Field(default=None, alias="maxChars")
    max_redirects: int | None = Field(default=None, alias="maxRedirects")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesPdfConfig(BaseModel):
    max_pages: int | None = Field(default=None, alias="maxPages")
    max_pixels: int | None = Field(default=None, alias="maxPixels")
    min_text_chars: int | None = Field(default=None, alias="minTextChars")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesImagesConfig(BaseModel):
    allow_url: bool | None = Field(default=None, alias="allowUrl")
    url_allowlist: list[str] | None = Field(default=None, alias="urlAllowlist")
    allowed_mimes: list[str] | None = Field(default=None, alias="allowedMimes")
    max_bytes: int | None = Field(default=None, alias="maxBytes")
    max_redirects: int | None = Field(default=None, alias="maxRedirects")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayHttpResponsesConfig(BaseModel):
    enabled: bool | None = None
    max_body_bytes: int | None = Field(default=None, alias="maxBodyBytes")
    max_url_parts: int | None = Field(default=None, alias="maxUrlParts")
    files: GatewayHttpResponsesFilesConfig | None = None
    images: GatewayHttpResponsesImagesConfig | None = None

    model_config = {"populate_by_name": True}


class GatewayHttpEndpointsConfig(BaseModel):
    chat_completions: GatewayHttpChatCompletionsConfig | None = Field(
        default=None, alias="chatCompletions"
    )
    responses: GatewayHttpResponsesConfig | None = None

    model_config = {"populate_by_name": True}


class GatewayHttpSecurityHeadersConfig(BaseModel):
    strict_transport_security: str | bool | None = Field(
        default=None, alias="strictTransportSecurity"
    )

    model_config = {"populate_by_name": True}


class GatewayHttpConfig(BaseModel):
    endpoints: GatewayHttpEndpointsConfig | None = None
    security_headers: GatewayHttpSecurityHeadersConfig | None = Field(
        default=None, alias="securityHeaders"
    )

    model_config = {"populate_by_name": True}


class GatewayPushApnsRelayConfig(BaseModel):
    base_url: str | None = Field(default=None, alias="baseUrl")
    timeout_ms: int | None = Field(default=None, alias="timeoutMs")

    model_config = {"populate_by_name": True}


class GatewayPushApnsConfig(BaseModel):
    relay: GatewayPushApnsRelayConfig | None = None


class GatewayPushConfig(BaseModel):
    apns: GatewayPushApnsConfig | None = None


class GatewayNodePairingConfig(BaseModel):
    auto_approve_cidrs: list[str] | None = Field(default=None, alias="autoApproveCidrs")

    model_config = {"populate_by_name": True}


class GatewayNodesConfig(BaseModel):
    browser: dict[str, Any] | None = None
    pairing: GatewayNodePairingConfig | None = None
    allow_commands: list[str] | None = Field(default=None, alias="allowCommands")
    deny_commands: list[str] | None = Field(default=None, alias="denyCommands")

    model_config = {"populate_by_name": True}


class GatewayToolsConfig(BaseModel):
    deny: list[str] | None = None
    allow: list[str] | None = None


class GatewayConfig(BaseModel):
    port: int | None = None
    mode: Literal["local", "remote"] | None = None
    bind: GatewayBindMode | None = None
    custom_bind_host: str | None = Field(default=None, alias="customBindHost")
    control_ui: GatewayControlUiConfig | None = Field(default=None, alias="controlUi")
    auth: GatewayAuthConfig | None = None
    tailscale: GatewayTailscaleConfig | None = None
    remote: GatewayRemoteConfig | None = None
    reload: GatewayReloadConfig | None = None
    tls: GatewayTlsConfig | None = None
    http: GatewayHttpConfig | None = None
    push: GatewayPushConfig | None = None
    nodes: GatewayNodesConfig | None = None
    trusted_proxies: list[str] | None = Field(default=None, alias="trustedProxies")
    allow_real_ip_fallback: bool | None = Field(default=None, alias="allowRealIpFallback")
    tools: GatewayToolsConfig | None = None
    handshake_timeout_ms: int | None = Field(default=None, alias="handshakeTimeoutMs")
    channel_health_check_minutes: int | None = Field(
        default=None, alias="channelHealthCheckMinutes"
    )
    channel_stale_event_threshold_minutes: int | None = Field(
        default=None, alias="channelStaleEventThresholdMinutes"
    )
    channel_max_restarts_per_hour: int | None = Field(
        default=None, alias="channelMaxRestartsPerHour"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}
