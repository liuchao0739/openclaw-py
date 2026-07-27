from typing import Dict, Any, Optional
from .__init__ import *


def load_deepinfra_extension():
    return {
        "id": "deepinfra",
        "providerDiscovery": deepinfra_provider_discovery,
        "onboard": {"applyConfig": apply_deepinfra_config},
        "cacheWrapper": {"create": create_deepinfra_anthropic_cache_wrapper},
        "media": {
            "imageGeneration": {"build": build_deepinfra_image_provider},
            "speech": {"build": build_deepinfra_speech_provider},
            "videoGeneration": {"build": build_deepinfra_video_provider},
            "mediaUnderstanding": {"build": build_deepinfra_media_understanding_provider},
            "embedding": {"build": build_deepinfra_embedding_provider},
            "memoryEmbedding": {"build": build_deepinfra_memory_embedding_provider},
        },
    }

__all__ = ["load_deepinfra_extension"]