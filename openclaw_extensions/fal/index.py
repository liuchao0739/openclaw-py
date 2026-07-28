from .__init__ import *


def load_fal_extension():
    return {
        "id": "fal",
        "providerRegistration": {"create": create_fal_provider},
        "onboard": {"applyConfig": apply_fal_config},
        "media": {
            "imageGeneration": {"build": build_fal_image_generation_provider},
            "musicGeneration": {"build": build_fal_music_generation_provider},
            "videoGeneration": {"build": build_fal_video_generation_provider},
        },
    }

__all__ = ["load_fal_extension"]