import re

_KIMI_MODEL_ID_PATTERN = re.compile(r"^kimi-k2(?:p[56]|[.-][56])(?:[-_].+)?$")


def is_fireworks_kimi_model_id(model_id: str) -> bool:
    normalized = model_id.strip().lower()
    parts = normalized.split("/")
    last_segment = parts[-1] if parts else normalized
    return bool(_KIMI_MODEL_ID_PATTERN.match(last_segment))
