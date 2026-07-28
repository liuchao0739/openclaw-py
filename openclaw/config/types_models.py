from __future__ import annotations

from typing import Any, Optional, List, Dict

from pydantic import BaseModel, Field


class ModelCompatConfig(BaseModel):
    supports_store: Optional[bool] = Field(default=None, alias="supportsStore")
    supports_developer_role: Optional[bool] = Field(default=None, alias="supportsDeveloperRole")
    supports_reasoning_effort: Optional[bool] = Field(default=None, alias="supportsReasoningEffort")
    supports_usage_in_streaming: Optional[bool] = Field(
        default=None, alias="supportsUsageInStreaming"
    )
    supports_strict_mode: Optional[bool] = Field(default=None, alias="supportsStrictMode")
    max_tokens_field: Optional[str] = Field(default=None, alias="maxTokensField")
    requires_tool_result_name: Optional[bool] = Field(
        default=None, alias="requiresToolResultName"
    )
    requires_assistant_after_tool_result: Optional[bool] = Field(
        default=None, alias="requiresAssistantAfterToolResult"
    )
    requires_thinking_as_text: Optional[bool] = Field(
        default=None, alias="requiresThinkingAsText"
    )
    requires_reasoning_content_on_assistant_messages: Optional[bool] = Field(
        default=None, alias="requiresReasoningContentOnAssistantMessages"
    )
    open_router_routing: Optional[bool] = Field(default=None, alias="openRouterRouting")
    vercel_gateway_routing: Optional[bool] = Field(default=None, alias="vercelGatewayRouting")
    zai_tool_stream: Optional[bool] = Field(default=None, alias="zaiToolStream")
    cache_control_format: Optional[str] = Field(default=None, alias="cacheControlFormat")
    send_session_affinity_headers: Optional[bool] = Field(
        default=None, alias="sendSessionAffinityHeaders"
    )
    supports_long_cache_retention: Optional[bool] = Field(
        default=None, alias="supportsLongCacheRetention"
    )
    thinking_format: Optional[str] = Field(default=None, alias="thinkingFormat")
    supported_reasoning_efforts: Optional[List[str]] = Field(
        default=None, alias="supportedReasoningEfforts"
    )
    reasoning_effort_map: Optional[Dict[str, str]] = Field(
        default=None, alias="reasoningEffortMap"
    )
    visible_reasoning_detail_types: Optional[List[str]] = Field(
        default=None, alias="visibleReasoningDetailTypes"
    )
    supports_tools: Optional[bool] = Field(default=None, alias="supportsTools")
    supports_prompt_cache_key: Optional[bool] = Field(
        default=None, alias="supportsPromptCacheKey"
    )
    requires_string_content: Optional[bool] = Field(
        default=None, alias="requiresStringContent"
    )
    strict_message_keys: Optional[bool] = Field(
        default=None, alias="strictMessageKeys"
    )
    tool_schema_profile: Optional[str] = Field(default=None, alias="toolSchemaProfile")
    unsupported_tool_schema_keywords: Optional[List[str]] = Field(
        default=None, alias="unsupportedToolSchemaKeywords"
    )
    native_web_search_tool: Optional[bool] = Field(
        default=None, alias="nativeWebSearchTool"
    )
    tool_call_arguments_encoding: Optional[str] = Field(
        default=None, alias="toolCallArgumentsEncoding"
    )
    requires_mistral_tool_ids: Optional[bool] = Field(
        default=None, alias="requiresMistralToolIds"
    )
    requires_open_ai_anthropic_tool_payload: Optional[bool] = Field(
        default=None, alias="requiresOpenAiAnthropicToolPayload"
    )
    send_session_id_header: Optional[bool] = Field(
        default=None, alias="sendSessionIdHeader"
    )
    supports_eager_tool_input_streaming: Optional[bool] = Field(
        default=None, alias="supportsEagerToolInputStreaming"
    )

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelImageInputConfig(BaseModel):
    max_bytes: Optional[int] = Field(default=None, alias="maxBytes")
    max_pixels: Optional[int] = Field(default=None, alias="maxPixels")
    max_side_px: Optional[int] = Field(default=None, alias="maxSidePx")
    preferred_side_px: Optional[int] = Field(default=None, alias="preferredSidePx")
    token_mode: Optional[str] = Field(default=None, alias="tokenMode")

    model_config = {"populate_by_name": True}


class ModelMediaInputConfig(BaseModel):
    image: Optional[ModelImageInputConfig] = None


class ModelProviderLocalServiceConfig(BaseModel):
    command: str
    args: Optional[List[str]] = None
    cwd: Optional[str] = None
    env: Optional[Dict[str, str]] = None
    health_url: Optional[str] = Field(default=None, alias="healthUrl")
    ready_timeout_ms: Optional[int] = Field(default=None, alias="readyTimeoutMs")
    idle_stop_ms: Optional[int] = Field(default=None, alias="idleStopMs")

    model_config = {"populate_by_name": True}


class ModelCostConfig(BaseModel):
    input: float
    output: float
    cache_read: float = Field(alias="cacheRead")
    cache_write: float = Field(alias="cacheWrite")
    tiered_pricing: Optional[List[Dict[str, Any]]] = Field(
        default=None, alias="tieredPricing"
    )

    model_config = {"populate_by_name": True}


class ModelDefinitionConfig(BaseModel):
    id: str
    name: str
    api: Optional[str] = None
    base_url: Optional[str] = Field(default=None, alias="baseUrl")
    reasoning: bool
    input: list[str]
    cost: ModelCostConfig
    context_window: int = Field(alias="contextWindow")
    context_tokens: Optional[int] = Field(default=None, alias="contextTokens")
    max_tokens: int = Field(alias="maxTokens")
    thinking_level_map: Optional[Dict[str, Any]] = Field(
        default=None, alias="thinkingLevelMap"
    )
    params: Optional[Dict[str, Any]] = None
    agent_runtime: Optional[Dict[str, Any]] = Field(default=None, alias="agentRuntime")
    headers: Optional[Dict[str, str]] = None
    compat: Optional[ModelCompatConfig] = None
    media_input: Optional[ModelMediaInputConfig] = Field(default=None, alias="mediaInput")
    metadata_source: Optional[str] = Field(default=None, alias="metadataSource")

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelProviderConfig(BaseModel):
    base_url: str = Field(alias="baseUrl")
    api_key: Optional[str] = Field(default=None, alias="apiKey")
    auth: Optional[str] = None
    api: Optional[str] = None
    context_window: Optional[int] = Field(default=None, alias="contextWindow")
    context_tokens: Optional[int] = Field(default=None, alias="contextTokens")
    max_tokens: Optional[int] = Field(default=None, alias="maxTokens")
    timeout_seconds: Optional[int] = Field(default=None, alias="timeoutSeconds")
    region: Optional[str] = None
    inject_num_ctx_for_openai_compat: Optional[bool] = Field(
        default=None, alias="injectNumCtxForOpenAICompat"
    )
    params: Optional[Dict[str, Any]] = None
    agent_runtime: Optional[Dict[str, Any]] = Field(default=None, alias="agentRuntime")
    local_service: Optional[ModelProviderLocalServiceConfig] = Field(
        default=None, alias="localService"
    )
    headers: Optional[Dict[str, str]] = None
    auth_header: Optional[bool] = Field(default=None, alias="authHeader")
    request: Optional[Dict[str, Any]] = None
    models: list[ModelDefinitionConfig] = []

    model_config = {"populate_by_name": True, "extra": "allow"}


class BedrockDiscoveryConfig(BaseModel):
    enabled: Optional[bool] = None
    region: Optional[str] = None
    provider_filter: Optional[List[str]] = Field(default=None, alias="providerFilter")
    refresh_interval: Optional[int] = Field(default=None, alias="refreshInterval")
    default_context_window: Optional[int] = Field(
        default=None, alias="defaultContextWindow"
    )
    default_max_tokens: Optional[int] = Field(default=None, alias="defaultMaxTokens")

    model_config = {"populate_by_name": True}


class DiscoveryToggleConfig(BaseModel):
    enabled: Optional[bool] = None


class ModelPricingConfig(BaseModel):
    enabled: Optional[bool] = None


class ModelsConfig(BaseModel):
    mode: Optional[str] = None
    providers: Optional[Dict[str, ModelProviderConfig]] = None
    pricing: Optional[ModelPricingConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}


class ModelsConfigInput(BaseModel):
    mode: Optional[str] = None
    providers: Optional[Dict[str, Any]] = None
    pricing: Optional[ModelPricingConfig] = None

    model_config = {"populate_by_name": True, "extra": "allow"}
