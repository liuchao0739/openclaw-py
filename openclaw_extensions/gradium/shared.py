import re

DEFAULT_GRADIUM_BASE_URL = "https://api.gradium.ai"
DEFAULT_GRADIUM_VOICE_ID = "YTpq7expH9539ERJ"

GRADIUM_VOICES = [
    {"id": "YTpq7expH9539ERJ", "name": "Emma"},
    {"id": "LFZvm12tW_z0xfGo", "name": "Kent"},
    {"id": "Eu9iL_CYe8N-Gkx_", "name": "Tiffany"},
    {"id": "2H4HY2CBNyJHBCrP", "name": "Christina"},
    {"id": "jtEKaLYNn6iif5PR", "name": "Sydney"},
    {"id": "KWJiFWu2O9nMPYcR", "name": "John"},
    {"id": "3jUdJyOi9pgbxBTK", "name": "Arthur"},
]


def normalize_gradium_base_url(base_url=None):
    if base_url is None:
        return DEFAULT_GRADIUM_BASE_URL
    trimmed = base_url.strip()
    trimmed = re.sub(r"/+$", "", trimmed)
    return trimmed or DEFAULT_GRADIUM_BASE_URL
