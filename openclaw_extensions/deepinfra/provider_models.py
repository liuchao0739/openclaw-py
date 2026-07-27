import json
import os
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, Set, Tuple, TypedDict, Union

with open(os.path.join(os.path.dirname(__file__), "openclaw.plugin.json")) as f:
    MANIFEST = json.load(f)

DEEPINFRA_MANIFEST_PROVIDER = MANIFEST["modelCatalog"]["providers"]["deepinfra"]
DEEPINFRA_BASE_URL = DEEPINFRA_MANIFEST_PROVIDER["baseUrl"]
DEEPINFRA_MODELS_URL = f"{DEEPINFRA_BASE_URL}/models?sort_by=openclaw&filter=with_meta"

DEEPINFRA_DEFAULT_MODEL_ID = "deepseek-ai/DeepSeek-V4-Flash"
DEEPINFRA_DEFAULT_MODEL_REF = f"deepinfra/{DEEPINFRA_DEFAULT_MODEL_ID}"

DEEPINFRA_DEFAULT_CONTEXT_WINDOW = 128000
DEEPINFRA_DEFAULT_MAX_TOKENS = 8192

DISCOVERY_TIMEOUT_MS = 5000
DISCOVERY_CACHE_TTL_MS = 5 * 60 * 1000


class DeepInfraAgentModelPricing(TypedDict, total=False):
    input_tokens: float
    output_tokens: float
    cache_read_tokens: float
    per_image_unit: float
    output_seconds: float
    input_characters: float
    input_seconds: float


class DeepInfraAgentModelMetadata(TypedDict, total=False):
    description: str
    context_length: Optional[int]
    max_tokens: Optional[int]
    pricing: DeepInfraAgentModelPricing
    tags: List[str]
    default_width: Optional[int]
    default_height: Optional[int]
    default_iterations: Optional[int]


class DeepInfraAgentModelEntry(TypedDict):
    id: str
    metadata: Optional[DeepInfraAgentModelMetadata]


DeepInfraSurface = Literal[
    "chat", "vlm", "embed", "image-gen", "video-gen", "tts", "stt"
]


@dataclass
class DeepInfraSurfaceModel:
    id: str
    name: str
    description: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    context_window: Optional[int] = None
    max_tokens: Optional[int] = None
    pricing: DeepInfraAgentModelPricing = field(default_factory=dict)
    default_width: Optional[int] = None
    default_height: Optional[int] = None
    default_iterations: Optional[int] = None


@dataclass
class DeepInfraDiscoveredCatalog:
    chat: List[DeepInfraSurfaceModel] = field(default_factory=list)
    vlm: List[DeepInfraSurfaceModel] = field(default_factory=list)
    embed: List[DeepInfraSurfaceModel] = field(default_factory=list)
    image_gen: List[DeepInfraSurfaceModel] = field(default_factory=list)
    video_gen: List[DeepInfraSurfaceModel] = field(default_factory=list)
    tts: List[DeepInfraSurfaceModel] = field(default_factory=list)
    stt: List[DeepInfraSurfaceModel] = field(default_factory=list)
    live: bool = False


SURFACE_FOR_TAG: Dict[str, DeepInfraSurface] = {
    "chat": "chat",
    "vlm": "vlm",
    "embed": "embed",
    "image-gen": "image-gen",
    "video-gen": "video-gen",
    "tts": "tts",
    "stt": "stt",
}


def as_positive_safe_integer(value: Optional[int]) -> Optional[int]:
    if value is None or value <= 0:
        return None
    return value


def entry_to_surface_model(entry: DeepInfraAgentModelEntry) -> Optional[DeepInfraSurfaceModel]:
    id_val = entry.get("id")
    if not isinstance(id_val, str) or not id_val.strip():
        return None

    metadata = entry.get("metadata")
    if not metadata:
        return None

    tags = [t for t in metadata.get("tags", []) if isinstance(t, str)]
    pricing: DeepInfraAgentModelPricing = metadata.get("pricing", {})

    return DeepInfraSurfaceModel(
        id=id_val.strip(),
        name=id_val.strip(),
        description=metadata.get("description"),
        tags=tags,
        context_window=as_positive_safe_integer(metadata.get("context_length")),
        max_tokens=as_positive_safe_integer(metadata.get("max_tokens")),
        pricing=pricing,
        default_width=as_positive_safe_integer(metadata.get("default_width")),
        default_height=as_positive_safe_integer(metadata.get("default_height")),
        default_iterations=as_positive_safe_integer(metadata.get("default_iterations")),
    )


def bucket_by_surface(models: List[DeepInfraSurfaceModel]) -> DeepInfraDiscoveredCatalog:
    catalog = DeepInfraDiscoveredCatalog(live=True)
    buckets: Dict[DeepInfraSurface, List[DeepInfraSurfaceModel]] = {
        "chat": catalog.chat,
        "vlm": catalog.vlm,
        "embed": catalog.embed,
        "image-gen": catalog.image_gen,
        "video-gen": catalog.video_gen,
        "tts": catalog.tts,
        "stt": catalog.stt,
    }

    for model in models:
        seen = set()
        for tag in model.tags:
            surface = SURFACE_FOR_TAG.get(tag)
            if surface and surface not in seen:
                seen.add(surface)
                buckets[surface].append(model)

    return catalog


STATIC_NON_CHAT_FALLBACK: List[DeepInfraSurfaceModel] = [
    DeepInfraSurfaceModel(
        id="black-forest-labs/FLUX-1-schnell",
        name="black-forest-labs/FLUX-1-schnell",
        tags=["image-gen"],
        pricing={"per_image_unit": 0.003},
        default_width=1024,
        default_height=1024,
        default_iterations=4,
    ),
    DeepInfraSurfaceModel(
        id="black-forest-labs/FLUX-1-dev",
        name="black-forest-labs/FLUX-1-dev",
        tags=["image-gen"],
        pricing={"per_image_unit": 0.025},
        default_width=1024,
        default_height=1024,
        default_iterations=28,
    ),
    DeepInfraSurfaceModel(
        id="Qwen/Qwen-Image-Max",
        name="Qwen/Qwen-Image-Max",
        tags=["image-gen"],
        pricing={"per_image_unit": 0.075},
        default_width=1024,
        default_height=1024,
        default_iterations=28,
    ),
    DeepInfraSurfaceModel(
        id="stabilityai/sdxl-turbo",
        name="stabilityai/sdxl-turbo",
        tags=["image-gen"],
        pricing={"per_image_unit": 0.0002},
        default_width=1024,
        default_height=1024,
        default_iterations=4,
    ),
    DeepInfraSurfaceModel(
        id="hexgrad/Kokoro-82M",
        name="hexgrad/Kokoro-82M",
        tags=["tts"],
        pricing={"input_characters": 0.65},
    ),
    DeepInfraSurfaceModel(
        id="Qwen/Qwen3-TTS",
        name="Qwen/Qwen3-TTS",
        tags=["tts"],
        pricing={"input_characters": 0.65},
    ),
    DeepInfraSurfaceModel(
        id="ResembleAI/chatterbox-turbo",
        name="ResembleAI/chatterbox-turbo",
        tags=["tts"],
        pricing={"input_characters": 1},
    ),
    DeepInfraSurfaceModel(
        id="sesame/csm-1b",
        name="sesame/csm-1b",
        tags=["tts"],
        pricing={"input_characters": 7},
    ),
    DeepInfraSurfaceModel(
        id="openai/whisper-large-v3-turbo",
        name="openai/whisper-large-v3-turbo",
        tags=["stt"],
        pricing={"input_seconds": 0.00004},
    ),
    DeepInfraSurfaceModel(
        id="BAAI/bge-m3",
        name="BAAI/bge-m3",
        tags=["embed"],
        pricing={"input_tokens": 0.01},
        max_tokens=8192,
        context_window=8192,
    ),
]


def manifest_fallback_catalog() -> DeepInfraDiscoveredCatalog:
    raw_chat = DEEPINFRA_MANIFEST_PROVIDER.get("models", [])
    chat_models = []

    for entry in raw_chat:
        cost = entry.get("cost", {})
        pricing: DeepInfraAgentModelPricing = {}
        if isinstance(cost.get("input"), (int, float)):
            pricing["input_tokens"] = float(cost["input"])
        if isinstance(cost.get("output"), (int, float)):
            pricing["output_tokens"] = float(cost["output"])
        if isinstance(cost.get("cacheRead"), (int, float)) and cost["cacheRead"] > 0:
            pricing["cache_read_tokens"] = float(cost["cacheRead"])

        tags = ["chat"]
        input_types = entry.get("input", [])
        if "image" in input_types:
            tags.append("vlm")
        if entry.get("reasoning"):
            tags.append("reasoning")

        chat_models.append(
            DeepInfraSurfaceModel(
                id=entry["id"],
                name=entry.get("name", entry["id"]),
                tags=tags,
                context_window=entry.get("contextWindow"),
                max_tokens=entry.get("maxTokens"),
                pricing=pricing,
            )
        )

    catalog = bucket_by_surface([*chat_models, *STATIC_NON_CHAT_FALLBACK])
    catalog.live = False
    return catalog


def get_deepinfra_surface_fallback_catalog() -> DeepInfraDiscoveredCatalog:
    return manifest_fallback_catalog()


def build_deepinfra_model_definition(model: Dict[str, Any]) -> Dict[str, Any]:
    compat = model.get("compat", {})
    return {
        **model,
        "compat": {
            **compat,
            "supportsUsageInStreaming": compat.get("supportsUsageInStreaming", True),
        },
    }


def chat_surface_model_to_model_definition(model: DeepInfraSurfaceModel) -> Dict[str, Any]:
    input_types: List[str] = ["text", "image"] if "vlm" in model.tags else ["text"]
    reasoning = "reasoning" in model.tags or "reasoning_effort" in model.tags

    return build_deepinfra_model_definition({
        "id": model.id,
        "name": model.name,
        "reasoning": reasoning,
        "input": input_types,
        "contextWindow": model.context_window or DEEPINFRA_DEFAULT_CONTEXT_WINDOW,
        "maxTokens": model.max_tokens or DEEPINFRA_DEFAULT_MAX_TOKENS,
        "cost": {
            "input": model.pricing.get("input_tokens", 0),
            "output": model.pricing.get("output_tokens", 0),
            "cacheRead": model.pricing.get("cache_read_tokens", 0),
            "cacheWrite": 0,
        },
    })


def has_deepinfra_api_key(options: Dict[str, Any] = None) -> bool:
    options = options or {}
    env = options.get("env", os.environ)

    from_env = env.get("DEEPINFRA_API_KEY")
    if isinstance(from_env, str) and from_env.strip():
        return True

    config = options.get("config", {})
    providers = config.get("models", {}).get("providers", {})

    for provider_id, provider in providers.items():
        if provider_id.strip().lower() == "deepinfra":
            api_key = provider.get("apiKey")
            if api_key:
                secrets_defaults = config.get("secrets", {}).get("defaults", {})
                if secrets_defaults.get("env") or secrets_defaults.get("file") or secrets_defaults.get("exec"):
                    return True
                if api_key:
                    return True

    agent_dir = options.get("agentDir")
    if agent_dir:
        auth_profile_path = os.path.join(agent_dir, "auth-profiles.json")
        if os.path.exists(auth_profile_path):
            return True

    return False


async def discover_deepinfra_surfaces(options: Dict[str, Any] = None) -> DeepInfraDiscoveredCatalog:
    options = options or {}

    if os.environ.get("NODE_ENV") == "test" or os.environ.get("VITEST"):
        return manifest_fallback_catalog()

    env = options.get("env", os.environ)
    has_key = options.get("hasApiKey") if "hasApiKey" in options else has_deepinfra_api_key({"env": env, "agentDir": options.get("agentDir")})

    if not has_key:
        return manifest_fallback_catalog()

    try:
        import httpx

        async with httpx.AsyncClient(timeout=DISCOVERY_TIMEOUT_MS / 1000) as client:
            response = await client.get(
                DEEPINFRA_MODELS_URL,
                headers={"Accept": "application/json"},
            )
            response.raise_for_status()
            data = response.json()
    except Exception:
        return manifest_fallback_catalog()

    if not data:
        return manifest_fallback_catalog()

    seen_ids: Set[str] = set()
    surface_models: List[DeepInfraSurfaceModel] = []

    for entry in data:
        model = entry_to_surface_model(entry)
        if not model or model.id in seen_ids:
            continue
        seen_ids.add(model.id)
        surface_models.append(model)

    if not surface_models:
        return manifest_fallback_catalog()

    return bucket_by_surface(surface_models)


async def discover_deepinfra_models(options: Dict[str, Any] = None) -> List[Dict[str, Any]]:
    catalog = await discover_deepinfra_surfaces(options)
    chat_models = catalog.chat
    if not chat_models:
        chat_models = [*catalog.chat, *catalog.vlm]

    if not chat_models:
        return [build_deepinfra_model_definition(m) for m in DEEPINFRA_MANIFEST_PROVIDER.get("models", [])]

    live_models = [chat_surface_model_to_model_definition(m) for m in chat_models]
    seen = {m["id"] for m in live_models}

    manifest_models = []
    for model in DEEPINFRA_MANIFEST_PROVIDER.get("models", []):
        if model["id"] not in seen:
            seen.add(model["id"])
            manifest_models.append(build_deepinfra_model_definition(model))

    return [*live_models, *manifest_models]