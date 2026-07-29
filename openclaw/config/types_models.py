from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class ModelCompatConfig(BaseModel):
    supports_store: bool | None = Field(default=None, alias="supportsStore")
    supports_developer_role: bool | None = Field(default=None, alias="supportsDeveloperRole")
    supports_reasoning_effort: bool | None = Field(default=None, alias="supportsReasoningEffort")
    supports_usage_in_streaming: bool | None = Field(
        default=None, alias="supportsUsageInStreaming"
    )
    supports_strict_mode: bool | None = Field(default=None, alias="supportsStrictMode")
    max_tokens_field: str | None = Field(default=None, alias="maxTokensField")
    requires_tool_result_name: bool | None = Field(
        default=None, alias="requiresToolResultName"
    )
    requires_assistant_after_tool_result: bool | None = Field(
        default=None, alias="requiresAssistantAfterToolResult"
    )
    requires_thinking_as_text: bool | None = Field(
        default=None, alias="requiresThinkingAsText"
    )
    requires_reasoning_content_on_assistant_messages: bool | None = Field(
        default=None, alias="requiresReasoningContentOnAssistantMessages"
    )
    open_router_routing: bool | None = Field(default=None, alias="openRouterRouting")
    vercel_gateway_routing: bool | None = Field(default=None, alias="vercelGatewayRouting")
    zai_tool_stream: bool | None = Field(default=None, alias="zaiToolStream")
    cache_control_format: str | None = Field(default=None, alias="cacheControlFormat")
    send_session_affinity_headers: bool | None = Field(
        default=None, alias="sendSessionAffinityHeaders"
    )
    supports_long_cache_retention: bool | None = Field(
        default=None, alias="supportsLongCacheRetention"
    )
    thinking_format: str | None = Field(default=None, alias="thinkingFormat")
    supported_reasoning_efforts: list[str] | None = Field(
        default=None, alias="supportedReasoningEfforts"
    )
    reasoning_effort_map: dict[str, str] | None = Field(
        default=None, alias="reasoningEffortMap"
    )
    visible_reasoning_detail_types: list[str] | None = Field(
        default=None, alias="visibleReasoningDetailTypes"
    )
    supports_tools: bool | None = Field(default=None, alias="supportsTools")
    supports_prompt_cache_key: bool | None = Field(
        default=None, alias="supportsPromptCacheKey"
    )
    requires_string_content: bool | None = Field(
        default=None, alias="requiresStringContent"
    )
    strict_message_keys: bool | None = Field(
        default=None, alias="strictMessageKeys"
    )
    tool_schema_profile: str | None = Field(default=None, alias="toolSchemaProfile")
    unsupported_tool_schema_keywords: list[str] | None = Field(
        default=None, alias="unsupportedToolSchemaKeywords"
    )
    native_web_search_tool: bool | None = Field(
        default=None, alias="nativeWebSearchTool"
    )
    tool_call_arguments_encoding: str | None = Field(
        default=None, alias="toolCallArgumentsEncoding"
    )
    requires_mistral_tool_ids: bool | None = Field(
        default=None, alias="requiresMistralToolIds"
    )
    requires_open_ai_anthropic_tool_payload: bool | None = Field(
        default=None, alias="requiresOpenAiAnthropicToolPayload"
    )
    send_session_id_header: bool | None = Field(
        default=None, alias="sendSessionIdHeader"
    )
    supports_eager_tool_input_streaming: bool | None = Field(
        default=None, alias="supportsEagerToolInputStreaming"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelImageInputConfig(BaseModel):
    max_bytes: int | None = Field(default=None, alias="maxBytes")
    max_pixels: int | None = Field(default=None, alias="maxPixels")
    max_side_px: int | None = Field(default=None, alias="maxSidePx")
    preferred_side_px: int | None = Field(default=None, alias="preferredSidePx")
    token_mode: str | None = Field(default=None, alias="tokenMode")

    model_config = {"populate_by_name": True}


class ModelMediaInputConfig(BaseModel):
    image: ModelImageInputConfig | None = None


class ModelProviderLocalServiceConfig(BaseModel):
    command: str
    args: list[str] | None = None
    cwd: str | None = None
    env: dict[str, str] | None = None
    health_url: str | None = Field(default=None, alias="healthUrl")
    ready_timeout_ms: int | None = Field(default=None, alias="readyTimeoutMs")
    idle_stop_ms: int | None = Field(default=None, alias="idleStopMs")

    model_config = {"populate_by_name": True}


class ModelCostConfig(BaseModel):
    input: float
    output: float
    cache_read: float = Field(alias="cacheRead")
    cache_write: float = Field(alias="cacheWrite")
    tiered_pricing: list[dict[str, Any]] | None = Field(
        default=None, alias="tieredPricing"
    )

    model_config = {"populate_by_name": True}


class ModelDefinitionConfig(BaseModel):
    id: str
    name: str
    api: str | None = None
    base_url: str | None = Field(default=None, alias="baseUrl")
    reasoning: bool
    input: list[str]
    cost: ModelCostConfig
    context_window: int = Field(alias="contextWindow")
    context_tokens: int | None = Field(default=None, alias="contextTokens")
    max_tokens: int = Field(alias="maxTokens")
    thinking_level_map: dict[str, Any] | None = Field(
        default=None, alias="thinkingLevelMap"
    )
    params: dict[str, Any] | None = None
    agent_runtime: dict[str, Any] | None = Field(default=None, alias="agentRuntime")
    headers: dict[str, str] | None = None
    compat: ModelCompatConfig | None = None
    media_input: ModelMediaInputConfig | None = Field(default=None, alias="mediaInput")
    metadata_source: str | None = Field(default=None, alias="metadataSource")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelProviderConfig(BaseModel):
    base_url: str = Field(alias="baseUrl")
    api_key: str | None = Field(default=None, alias="apiKey")
    auth: str | None = None
    api: str | None = None
    context_window: int | None = Field(default=None, alias="contextWindow")
    context_tokens: int | None = Field(default=None, alias="contextTokens")
    max_tokens: int | None = Field(default=None, alias="maxTokens")
    timeout_seconds: int | None = Field(default=None, alias="timeoutSeconds")
    region: str | None = None
    inject_num_ctx_for_openai_compat: bool | None = Field(
        default=None, alias="injectNumCtxForOpenAICompat"
    )
    params: dict[str, Any] | None = None
    agent_runtime: dict[str, Any] | None = Field(default=None, alias="agentRuntime")
    local_service: ModelProviderLocalServiceConfig | None = Field(
        default=None, alias="localService"
    )
    headers: dict[str, str] | None = None
    auth_header: bool | None = Field(default=None, alias="authHeader")
    request: dict[str, Any] | None = None
    models: list[ModelDefinitionConfig] = []

    model_config = {"populate_by_name": True, "extra": "allow"}


class BedrockDiscoveryConfig(BaseModel):
    enabled: bool | None = None
    region: str | None = None
    provider_filter: list[str] | None = Field(default=None, alias="providerFilter")
    refresh_interval: int | None = Field(default=None, alias="refreshInterval")
    default_context_window: int | None = Field(
        default=None, alias="defaultContextWindow"
    )
    default_max_tokens: int | None = Field(default=None, alias="defaultMaxTokens")

    model_config = {"populate_by_name": True}


class DiscoveryToggleConfig(BaseModel):
    enabled: bool | None = None


class ModelPricingConfig(BaseModel):
    enabled: bool | None = None


class ModelsConfig(BaseModel):
    mode: str | None = None
    providers: dict[str, ModelProviderConfig] | None = None
    pricing: ModelPricingConfig | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelsConfigInput(BaseModel):
    mode: str | None = None
    providers: dict[str, Any] | None = None
    pricing: ModelPricingConfig | None = None

    model_config = {"populate_by_name": True, "extra": "allow"}
