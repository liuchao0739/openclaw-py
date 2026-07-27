DEEPINFRA_NATIVE_BASE_URL = "https://api.deepinfra.com/v1/inference"

DEFAULT_DEEPINFRA_IMAGE_SIZE = "1024x1024"
DEFAULT_DEEPINFRA_TTS_VOICE = "af_bella"
DEEPINFRA_VIDEO_ASPECT_RATIOS = ["16:9", "4:3", "1:1", "3:4", "9:16"]
DEEPINFRA_VIDEO_DURATIONS = [5, 8]

DEEPINFRA_IMAGE_FALLBACK_MODELS = [
    "black-forest-labs/FLUX-1-schnell",
    "run-diffusion/Juggernaut-Lightning-Flux",
    "black-forest-labs/FLUX-1-dev",
    "Qwen/Qwen-Image-Max",
    "stabilityai/sdxl-turbo",
]

DEEPINFRA_TTS_FALLBACK_MODELS = [
    "hexgrad/Kokoro-82M",
    "Qwen/Qwen3-TTS",
    "ResembleAI/chatterbox-turbo",
    "sesame/csm-1b",
]

DEEPINFRA_VIDEO_FALLBACK_MODELS = [
    "Pixverse/Pixverse-T2V",
    "Pixverse/Pixverse-T2V-HD",
    "Wan-AI/Wan2.6-T2V",
    "google/veo-3.1-fast",
]

DEEPINFRA_STT_FALLBACK_MODELS = [
    "openai/whisper-large-v3-turbo",
    "openai/whisper-large-v3",
]

DEEPINFRA_EMBED_FALLBACK_MODELS = ["BAAI/bge-m3"]

DEEPINFRA_VLM_FALLBACK_MODELS = ["moonshotai/Kimi-K2.5"]


def normalize_deepinfra_model_ref(model: str | None, fallback: str) -> str:
    value = model.strip() if model else fallback
    return value[len("deepinfra/") :] if value.startswith("deepinfra/") else value


def normalize_deepinfra_base_url(value: str | None, fallback: str = "") -> str:
    if not value:
        return fallback
    return value.rstrip("/")