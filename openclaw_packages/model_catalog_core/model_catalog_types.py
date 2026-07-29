from typing import Any, List, Literal, Optional, Sequence, Tuple, TypedDict, Union

MODEL_CATALOG_APIS: Tuple[str, ...] = (
    "openai-completions",
    "openai-responses",
    "openai-chatgpt-responses",
    "anthropic-messages",
    "google-generative-ai",
    "google-vertex",
    "github-copilot",
    "bedrock-converse-stream",
    "ollama",
    "azure-openai-responses",
)

ModelCatalogApi = Literal[
    "openai-completions",
    "openai-responses",
    "openai-chatgpt-responses",
    "anthropic-messages",
    "google-generative-ai",
    "google-vertex",
    "github-copilot",
    "bedrock-converse-stream",
    "ollama",
    "azure-openai-responses",
]

MODEL_CATALOG_THINKING_FORMATS: Tuple[str, ...] = (
    "openai",
    "openrouter",
    "deepseek",
    "together",
    "qwen",
    "qwen-chat-template",
    "zai",
)

ModelCatalogThinkingFormat = Literal[
    "openai",
    "openrouter",
    "deepseek",
    "together",
    "qwen",
    "qwen-chat-template",
    "zai",
]


def is_model_catalog_thinking_format(value: str) -> bool:
    return value in MODEL_CATALOG_THINKING_FORMATS


class ModelCatalogOpenRouterRoutingSortObject(TypedDict, total=False):
    by: str
    partition: Optional[str]


class ModelCatalogOpenRouterMaxPrice(TypedDict, total=False):
    prompt: Union[int, float, str]
    completion: Union[int, float, str]
    image: Union[int, float, str]
    audio: Union[int, float, str]
    request: Union[int, float, str]


class ModelCatalogOpenRouterPercentileCutoffs(TypedDict, total=False):
    p50: float
    p75: float
    p90: float
    p99: float


class ModelCatalogOpenRouterRouting(TypedDict, total=False):
    allow_fallbacks: bool
    require_parameters: bool
    data_collection: Literal["deny", "allow"]
    zdr: bool
    enforce_distillable_text: bool
    order: List[str]
    only: List[str]
    ignore: List[str]
    quantizations: List[str]
    sort: Union[str, ModelCatalogOpenRouterRoutingSortObject]
    max_price: ModelCatalogOpenRouterMaxPrice
    preferred_min_throughput: Union[float, ModelCatalogOpenRouterPercentileCutoffs]
    preferred_max_latency: Union[float, ModelCatalogOpenRouterPercentileCutoffs]


class ModelCatalogVercelGatewayRouting(TypedDict, total=False):
    only: List[str]
    order: List[str]


class ModelCatalogImageInputConfig(TypedDict, total=False):
    maxBytes: int
    maxPixels: int
    maxSidePx: int
    preferredSidePx: int
    tokenMode: Literal["tile", "detail", "provider"]


class ModelCatalogMediaInputConfig(TypedDict, total=False):
    image: ModelCatalogImageInputConfig


ModelCatalogInput = Literal["text", "image", "document"]
ModelCatalogDiscovery = Literal["static", "refreshable", "runtime"]
ModelCatalogStatus = Literal["available", "preview", "deprecated", "disabled"]
ModelCatalogSource = Literal[
    "manifest",
    "provider-index",
    "cache",
    "config",
    "runtime-refresh",
]

UnifiedModelCatalogKind = Literal[
    "text",
    "voice",
    "image_generation",
    "video_generation",
    "music_generation",
]

UnifiedModelCatalogSource = Literal[
    "manifest",
    "provider-index",
    "static",
    "live",
    "cache",
    "configured",
    "runtime-refresh",
]


class UnifiedModelCatalogEntry(TypedDict, total=False):
    kind: UnifiedModelCatalogKind
    provider: str
    model: str
    label: str
    source: UnifiedModelCatalogSource
    default: bool
    configured: bool
    capabilities: Any
    modes: Sequence[str]
    authEnvVars: Sequence[str]
    docsPath: str
    fetchedAt: int
    expiresAt: int
    warnings: Sequence[str]


class ModelCatalogTieredCost(TypedDict):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float
    range: Union[Tuple[float], Tuple[float, float]]


class ModelCatalogCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float
    tieredPricing: List[ModelCatalogTieredCost]


class ModelCatalogCompatConfig(TypedDict, total=False):
    supportsStore: bool
    supportsDeveloperRole: bool
    supportsReasoningEffort: bool
    supportsUsageInStreaming: bool
    supportsStrictMode: bool
    maxTokensField: Literal["max_completion_tokens", "max_tokens"]
    requiresToolResultName: bool
    requiresAssistantAfterToolResult: bool
    requiresThinkingAsText: bool
    openRouterRouting: ModelCatalogOpenRouterRouting
    vercelGatewayRouting: ModelCatalogVercelGatewayRouting
    zaiToolStream: bool
    cacheControlFormat: Literal["anthropic"]
    sendSessionAffinityHeaders: bool
    sendSessionIdHeader: bool
    supportsEagerToolInputStreaming: bool
    supportsLongCacheRetention: bool
    supportsPromptCacheKey: bool
    supportsTools: bool
    requiresStringContent: bool
    strictMessageKeys: bool
    toolSchemaProfile: str
    unsupportedToolSchemaKeywords: List[str]
    nativeWebSearchTool: bool
    toolCallArgumentsEncoding: str
    requiresMistralToolIds: bool
    requiresOpenAiAnthropicToolPayload: bool
    thinkingFormat: ModelCatalogThinkingFormat
    supportedReasoningEfforts: List[str]
    reasoningEffortMap: dict
    visibleReasoningDetailTypes: List[str]


class ModelCatalogModel(TypedDict, total=False):
    id: str
    name: str
    api: ModelCatalogApi
    baseUrl: str
    headers: dict
    input: List[ModelCatalogInput]
    reasoning: bool
    contextWindow: float
    contextTokens: int
    maxTokens: float
    cost: ModelCatalogCost
    compat: ModelCatalogCompatConfig
    mediaInput: ModelCatalogMediaInputConfig
    status: ModelCatalogStatus
    statusReason: str
    replaces: List[str]
    replacedBy: str
    tags: List[str]


class ModelCatalogProvider(TypedDict, total=False):
    baseUrl: str
    api: ModelCatalogApi
    headers: dict
    models: List[ModelCatalogModel]


class ModelCatalogAlias(TypedDict, total=False):
    provider: str
    api: ModelCatalogApi
    baseUrl: str


class ModelCatalogSuppressionWhen(TypedDict, total=False):
    baseUrlHosts: List[str]
    providerConfigApiIn: List[str]


class ModelCatalogSuppression(TypedDict, total=False):
    provider: str
    model: str
    reason: str
    when: ModelCatalogSuppressionWhen


class ModelCatalog(TypedDict, total=False):
    providers: dict
    aliases: dict
    suppressions: List[ModelCatalogSuppression]
    discovery: dict
    runtimeAugment: bool


class NormalizedModelCatalogRow(TypedDict, total=False):
    provider: str
    id: str
    ref: str
    mergeKey: str
    name: str
    source: ModelCatalogSource
    input: List[ModelCatalogInput]
    reasoning: bool
    status: ModelCatalogStatus
    api: ModelCatalogApi
    baseUrl: str
    headers: dict
    contextWindow: float
    contextTokens: int
    maxTokens: float
    cost: ModelCatalogCost
    compat: ModelCatalogCompatConfig
    mediaInput: ModelCatalogMediaInputConfig
    statusReason: str
    replaces: List[str]
    replacedBy: str
    tags: List[str]
