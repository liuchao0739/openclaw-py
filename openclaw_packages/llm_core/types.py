from typing import Any, Callable, Dict, List, Literal, Optional, Sequence, TypedDict, Union

KnownApi = Literal[
    "openai-completions",
    "mistral-conversations",
    "openai-responses",
    "azure-openai-responses",
    "openai-chatgpt-responses",
    "anthropic-messages",
    "bedrock-converse-stream",
    "google-generative-ai",
    "google-vertex",
]

Api = str

KnownImagesApi = Literal["openrouter-images"]

ImagesApi = str

Provider = str

KnownImagesProvider = Literal["openrouter"]

ImagesProvider = str

ThinkingLevel = Literal["minimal", "low", "medium", "high", "xhigh", "max"]

ModelThinkingLevel = Union[Literal["off"], ThinkingLevel]

ThinkingLevelMap = Dict[str, Optional[str]]


class ThinkingBudgets(TypedDict, total=False):
    minimal: float
    low: float
    medium: float
    high: float
    max: float


CacheRetention = Literal["none", "short", "long"]

Transport = Literal["sse", "websocket", "websocket-cached", "auto"]

MaybePromise = Any


class ProviderResponse(TypedDict):
    status: int
    headers: Dict[str, str]


class StreamOptions(TypedDict, total=False):
    temperature: float
    maxTokens: float
    stop: List[str]
    signal: Any
    apiKey: str
    transport: Transport
    cacheRetention: CacheRetention
    sessionId: str
    promptCacheKey: str
    onPayload: Callable[[Any, "Model"], Any]
    onResponse: Callable[[ProviderResponse, "Model"], Any]
    headers: Dict[str, str]
    timeoutMs: float
    maxRetries: float
    maxRetryDelayMs: float
    metadata: Dict[str, Any]


ProviderStreamOptions = StreamOptions


class ImagesOptions(TypedDict, total=False):
    signal: Any
    apiKey: str
    onPayload: Callable[[Any, "ImagesModel"], Any]
    onResponse: Callable[[ProviderResponse, "ImagesModel"], Any]
    headers: Dict[str, str]
    timeoutMs: float
    maxRetries: float
    maxRetryDelayMs: float
    metadata: Dict[str, Any]


ProviderImagesOptions = ImagesOptions


class SimpleStreamOptions(StreamOptions, total=False):
    reasoning: ThinkingLevel
    thinkingBudgets: ThinkingBudgets


class TextSignatureV1(TypedDict):
    v: int
    id: str
    phase: Optional[Literal["commentary", "final_answer"]]


class TextContent(TypedDict, total=False):
    type: str
    text: str
    textSignature: str


class ThinkingContent(TypedDict, total=False):
    type: str
    thinking: str
    thinkingSignature: str
    redacted: bool


class ImageContent(TypedDict, total=False):
    type: str
    data: str
    mimeType: str


class ToolCall(TypedDict, total=False):
    type: str
    id: str
    name: str
    arguments: Dict[str, Any]
    thoughtSignature: str
    executionMode: Literal["sequential", "parallel"]


class UsageCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float
    total: float


class Usage(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float
    totalTokens: float
    cost: UsageCost


StopReason = Literal["stop", "length", "toolUse", "error", "aborted"]


class UserMessage(TypedDict, total=False):
    role: str
    content: Union[str, List[Union[TextContent, ImageContent]]]
    timestamp: float


class AssistantMessage(TypedDict, total=False):
    role: str
    content: List[Union[TextContent, ThinkingContent, ToolCall]]
    api: Api
    provider: Provider
    model: str
    responseModel: str
    responseId: str
    diagnostics: List[Any]
    usage: Usage
    stopReason: StopReason
    errorMessage: str
    errorCode: str
    errorType: str
    errorBody: str
    timestamp: float


class ToolResultMessage(TypedDict, total=False):
    role: str
    toolCallId: str
    toolName: str
    content: List[Union[TextContent, ImageContent]]
    details: Any
    isError: bool
    timestamp: float


Message = Union[UserMessage, AssistantMessage, ToolResultMessage]

ImagesInputContent = Union[TextContent, ImageContent]
ImagesOutputContent = Union[TextContent, ImageContent]


class ImagesContext(TypedDict, total=False):
    input: List[ImagesInputContent]


ImagesStopReason = Literal["stop", "error", "aborted"]


class AssistantImages(TypedDict, total=False):
    api: ImagesApi
    provider: ImagesProvider
    model: str
    output: List[ImagesOutputContent]
    responseId: str
    usage: Usage
    stopReason: ImagesStopReason
    errorMessage: str
    timestamp: float


class Tool(TypedDict, total=False):
    name: str
    description: str
    parameters: Dict[str, Any]


class Context(TypedDict, total=False):
    systemPrompt: str
    messages: List[Message]
    tools: List[Tool]


class AssistantMessageEvent(TypedDict, total=False):
    type: str
    partial: AssistantMessage
    contentIndex: int
    delta: str
    content: str
    toolCall: ToolCall
    reason: str
    message: AssistantMessage
    error: AssistantMessage


AssistantMessageEventStreamContract = Any
AssistantMessageEventStreamLike = Any


class OpenRouterRoutingMaxPrice(TypedDict, total=False):
    prompt: Union[float, str]
    completion: Union[float, str]
    image: Union[float, str]
    audio: Union[float, str]
    request: Union[float, str]


class OpenRouterRoutingSortObject(TypedDict, total=False):
    by: str
    partition: Optional[str]


class OpenRouterRoutingPreferredPercentiles(TypedDict, total=False):
    p50: float
    p75: float
    p90: float
    p99: float


class OpenRouterRouting(TypedDict, total=False):
    allow_fallbacks: bool
    require_parameters: bool
    data_collection: Literal["deny", "allow"]
    zdr: bool
    enforce_distillable_text: bool
    order: List[str]
    only: List[str]
    ignore: List[str]
    quantizations: List[str]
    sort: Union[str, OpenRouterRoutingSortObject]
    max_price: OpenRouterRoutingMaxPrice
    preferred_min_throughput: Union[float, OpenRouterRoutingPreferredPercentiles]
    preferred_max_latency: Union[float, OpenRouterRoutingPreferredPercentiles]


class VercelGatewayRouting(TypedDict, total=False):
    only: List[str]
    order: List[str]


class OpenAICompletionsCompat(TypedDict, total=False):
    supportsStore: bool
    supportsDeveloperRole: bool
    supportsReasoningEffort: bool
    supportsUsageInStreaming: bool
    maxTokensField: Literal["max_completion_tokens", "max_tokens"]
    requiresToolResultName: bool
    requiresAssistantAfterToolResult: bool
    requiresThinkingAsText: bool
    requiresReasoningContentOnAssistantMessages: bool
    thinkingFormat: Literal["openai", "openrouter", "deepseek", "together", "zai", "qwen", "qwen-chat-template"]
    openRouterRouting: OpenRouterRouting
    vercelGatewayRouting: VercelGatewayRouting
    zaiToolStream: bool
    supportsStrictMode: bool
    cacheControlFormat: Literal["anthropic"]
    sendSessionAffinityHeaders: bool
    supportsPromptCacheKey: bool
    supportsLongCacheRetention: bool


class OpenAIResponsesCompat(TypedDict, total=False):
    sendSessionIdHeader: bool
    supportsLongCacheRetention: bool


class AnthropicMessagesCompat(TypedDict, total=False):
    supportsEagerToolInputStreaming: bool
    supportsLongCacheRetention: bool
    sendSessionAffinityHeaders: bool
    supportsCacheControlOnTools: bool


class ModelMediaInputImage(TypedDict, total=False):
    maxBytes: float
    maxPixels: float
    maxSidePx: float
    preferredSidePx: float
    tokenMode: Literal["tile", "detail", "provider"]


class ModelMediaInput(TypedDict, total=False):
    image: ModelMediaInputImage


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


class Model(TypedDict, total=False):
    id: str
    name: str
    api: Api
    provider: Provider
    baseUrl: str
    reasoning: bool
    thinkingLevelMap: ThinkingLevelMap
    input: List[Literal["text", "image"]]
    cost: ModelCost
    contextWindow: float
    contextTokens: float
    maxTokens: float
    params: Dict[str, Any]
    headers: Dict[str, str]
    authHeader: bool
    compat: Union[OpenAICompletionsCompat, OpenAIResponsesCompat, AnthropicMessagesCompat]
    mediaInput: ModelMediaInput


class ImagesModel(TypedDict, total=False):
    id: str
    name: str
    api: ImagesApi
    provider: ImagesProvider
    baseUrl: str
    thinkingLevelMap: ThinkingLevelMap
    input: List[Literal["text", "image"]]
    cost: ModelCost
    contextWindow: float
    contextTokens: float
    maxTokens: float
    params: Dict[str, Any]
    headers: Dict[str, str]
    authHeader: bool
    output: List[Literal["text", "image"]]
    mediaInput: ModelMediaInput


StreamFunction = Callable[..., Any]
ImagesFunction = Callable[..., Any]
StreamFn = Callable[..., Any]
CompleteSimpleFn = Callable[..., Any]
ValidateToolArgumentsFn = Callable[[Tool, ToolCall], Any]
