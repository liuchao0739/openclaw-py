import math

from .defaults import DEFAULT_VIDEO_MAX_BASE64_BYTES


def estimate_base64_size(num_bytes: int) -> int:
    return math.ceil(num_bytes / 3) * 4


def resolve_video_max_base64_bytes(max_bytes: int) -> int:
    expanded = estimate_base64_size(max_bytes)
    return min(expanded, DEFAULT_VIDEO_MAX_BASE64_BYTES)
