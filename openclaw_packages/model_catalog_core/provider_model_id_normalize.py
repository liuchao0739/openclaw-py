from typing import Set

ANTIGRAVITY_BARE_PRO_IDS: Set[str] = {"gemini-3-pro", "gemini-3.1-pro", "gemini-3-1-pro"}
GOOGLE_PROVIDER_PREFIX = "google/"


def normalize_google_preview_model_id(id: str) -> str:
    if id.startswith(GOOGLE_PROVIDER_PREFIX):
        model_id = id[len(GOOGLE_PROVIDER_PREFIX):]
        normalized_model_id = normalize_google_preview_model_id(model_id)
        return id if normalized_model_id == model_id else f"{GOOGLE_PROVIDER_PREFIX}{normalized_model_id}"
    if id == "gemini-3-pro" or id == "gemini-3-pro-preview":
        return "gemini-3.1-pro-preview"
    if id == "gemini-3-flash":
        return "gemini-3-flash-preview"
    if id == "gemini-3.1-pro":
        return "gemini-3.1-pro-preview"
    if id == "gemini-3.1-flash-lite-preview":
        return "gemini-3.1-flash-lite"
    if id == "gemini-3.1-flash" or id == "gemini-3.1-flash-preview":
        return "gemini-3-flash-preview"
    if id == "gemma-4-26b":
        return "gemma-4-26b-a4b-it"
    return id


def normalize_together_model_id(id: str) -> str:
    if id == "moonshotai/Kimi-K2.5":
        return "moonshotai/Kimi-K2.6"
    return id


def normalize_antigravity_preview_model_id(id: str) -> str:
    if id in ANTIGRAVITY_BARE_PRO_IDS:
        return f"{id}-low"
    return id
