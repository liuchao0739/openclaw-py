import re
from typing import Optional, Tuple


GOOGLE_MODEL_ID_PREFIXES = [
    "google/",
    "google:",
    "google-",
    "vertex/",
    "vertex:",
    "vertex-",
]

GOOGLE_PROVIDER_MODEL_PREFIX_MAP = {
    "google/": "google/",
    "google:": "google/",
    "google-": "google/",
    "vertex/": "vertex/",
    "vertex:": "vertex/",
    "vertex-": "vertex/",
}

GOOGLE_PROVIDER_ALIASES = {
    "google": "google/",
    "vertex": "vertex/",
    "google_ai": "google/",
    "googleai": "google/",
    "googlegemini": "google/",
    "gemini": "google/",
}

DEFAULT_GOOGLE_PROVIDER_MODEL = "google/"

GOOGLE_MODEL_ID_CANONICAL_RE = re.compile(r"^(google|vertex)[/:](.+)$", re.IGNORECASE)


def strip_google_provider_prefix(model_id: str) -> str:
    if not model_id:
        return model_id
    for prefix in GOOGLE_MODEL_ID_PREFIXES:
        if model_id.lower().startswith(prefix.lower()):
            return model_id[len(prefix):]
    return model_id


def normalize_google_model_id(model_id: str, provider: Optional[str] = None) -> str:
    if not model_id:
        return model_id
    stripped = strip_google_provider_prefix(model_id)
    if provider:
        alias = GOOGLE_PROVIDER_ALIASES.get(provider.lower())
        if alias:
            return alias + stripped
    return DEFAULT_GOOGLE_PROVIDER_MODEL + stripped


def parse_google_model_id(model_id: str) -> Tuple[Optional[str], str]:
    if not model_id:
        return None, ""
    match = GOOGLE_MODEL_ID_CANONICAL_RE.match(model_id)
    if match:
        provider = match.group(1).lower()
        model = match.group(2)
        return provider, model
    stripped = strip_google_provider_prefix(model_id)
    return None, stripped


def is_google_model_id(model_id: str) -> bool:
    if not model_id:
        return False
    for prefix in GOOGLE_MODEL_ID_PREFIXES:
        if model_id.lower().startswith(prefix.lower()):
            return True
    return False


def infer_google_provider_from_model_id(model_id: str) -> str:
    if not model_id:
        return "google/"
    match = GOOGLE_MODEL_ID_CANONICAL_RE.match(model_id)
    if match:
        provider = match.group(1).lower()
        return provider + "/"
    if "vertex" in model_id.lower():
        return "vertex/"
    return "google/"


GOOGLE_MODEL_ID_ALIASES = {
    "gemini-pro": "google/gemini-2.0-flash",
    "gemini-pro-1.0": "google/gemini-1.0-pro",
    "gemini-pro-1.5": "google/gemini-1.5-pro",
    "gemini-pro-2.0": "google/gemini-2.0-pro",
    "gemini-pro-2.5": "google/gemini-2.5-pro",
    "gemini-flash": "google/gemini-2.0-flash",
    "gemini-flash-1.0": "google/gemini-1.0-flash",
    "gemini-flash-1.5": "google/gemini-1.5-flash",
    "gemini-flash-2.0": "google/gemini-2.0-flash",
    "gemini-flash-2.5": "google/gemini-2.5-flash",
    "gemini-ultra": "google/gemini-1.0-ultra",
    "gemini-ultra-1.0": "google/gemini-1.0-ultra",
    "gemini-ultra-1.5": "google/gemini-1.5-ultra",
    "gemini-ultra-2.0": "google/gemini-2.0-ultra",
    "gemini-ultra-2.5": "google/gemini-2.5-ultra",
    "gemini-2.0-pro": "google/gemini-2.0-pro",
    "gemini-2.0-flash": "google/gemini-2.0-flash",
    "gemini-2.0-pro-exp": "google/gemini-2.0-pro-exp",
    "gemini-2.0-flash-exp": "google/gemini-2.0-flash-exp",
    "gemini-1.5-pro": "google/gemini-1.5-pro",
    "gemini-1.5-flash": "google/gemini-1.5-flash",
    "gemini-1.5-pro-002": "google/gemini-1.5-pro-002",
    "gemini-1.5-flash-002": "google/gemini-1.5-flash-002",
    "gemini-1.0-pro": "google/gemini-1.0-pro",
    "gemini-1.0-pro-001": "google/gemini-1.0-pro-001",
    "gemini-1.0-flash": "google/gemini-1.0-flash",
    "gemini-1.0-flash-001": "google/gemini-1.0-flash-001",
    "gemini-1.0-ultra": "google/gemini-1.0-ultra",
    "gemini-1.0-ultra-001": "google/gemini-1.0-ultra-001",
    "gemini-1.0-pro-latest": "google/gemini-1.0-pro",
    "gemini-1.0-flash-latest": "google/gemini-1.0-flash",
    "gemini-1.0-ultra-latest": "google/gemini-1.0-ultra",
    "gemini-1.0-pro-vision": "google/gemini-1.0-pro-vision",
    "gemini-1.0-pro-vision-001": "google/gemini-1.0-pro-vision-001",
    "text-bison": "google/text-bison",
    "text-bison-001": "google/text-bison-001",
    "text-bison@001": "google/text-bison-001",
    "chat-bison": "google/chat-bison",
    "chat-bison-001": "google/chat-bison-001",
    "chat-bison@001": "google/chat-bison-001",
    "embedding-gecko": "google/embedding-gecko",
    "embedding-gecko-001": "google/embedding-gecko-001",
    "embedding-gecko@001": "google/embedding-gecko-001",
    "embedding-gecko-3": "google/embedding-gecko-3",
    "embedding-gecko-3-001": "google/embedding-gecko-3-001",
    "embedding-001": "google/embedding-001",
    "text-embedding-004": "google/text-embedding-004",
    "text-embedding-005": "google/text-embedding-005",
    "imagen": "google/imagen",
    "imagen-3.0": "google/imagen-3.0",
    "imagen-3.0-generate-001": "google/imagen-3.0-generate-001",
    "veo": "google/veo",
    "veo-2.0": "google/veo-2.0",
    "veo-2.0-generate-001": "google/veo-2.0-generate-001",
    "veo-3.0": "google/veo-3.0",
    "veo-3.0-generate-001": "google/veo-3.0-generate-001",
    "audio": "google/audio",
    "audio-2.0": "google/audio-2.0",
    "audio-2.0-generate-001": "google/audio-2.0-generate-001",
    "music": "google/music",
    "music-2.0": "google/music-2.0",
    "music-2.0-generate-001": "google/music-2.0-generate-001",
}