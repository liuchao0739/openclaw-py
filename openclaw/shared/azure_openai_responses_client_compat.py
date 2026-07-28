"""Azure OpenAI responses client compatibility helpers."""

from __future__ import annotations

from urllib.parse import urlparse


def is_traditional_azure_openai_host(hostname: str) -> bool:
    return (
        hostname.endswith(".openai.azure.com")
        or hostname.endswith(".cognitiveservices.azure.com")
    )


def is_openai_compatible_azure_responses_base_url(base_url: str) -> bool:
    try:
        parsed = urlparse(base_url)
    except Exception:
        return False
    if is_traditional_azure_openai_host(parsed.hostname):
        return False
    hostname = parsed.hostname.lower() if parsed.hostname else ""
    is_foundry_host = (
        hostname.endswith(".services.ai.azure.com")
        or hostname.endswith(".api.cognitive.microsoft.com")
    )
    if not is_foundry_host:
        return False
    normalized_path = parsed.path.rstrip("/")
    return normalized_path == "/openai/v1" or normalized_path.endswith("/openai/v1")
