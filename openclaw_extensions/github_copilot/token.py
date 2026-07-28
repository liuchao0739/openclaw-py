from typing import Dict, Optional

DEFAULT_COPILOT_API_BASE_URL = "https://api.individual.githubcopilot.com"


async def resolveCopilotApiToken(params: Dict) -> Dict:
    githubToken = params.get("githubToken")
    env = params.get("env") or {}
    fetchImpl = params.get("fetchImpl")

    import requests
    if fetchImpl:
        response = await fetchImpl("https://api.github.com/copilot_internal/v2/token", headers={"Authorization": f"Bearer {githubToken}"})
        data = await response.json()
    else:
        response = requests.get("https://api.github.com/copilot_internal/v2/token", headers={"Authorization": f"Bearer {githubToken}"})
        data = response.json()

    token = data.get("token")
    expiresAt = data.get("expires_at")
    baseUrl = data.get("base_url", DEFAULT_COPILOT_API_BASE_URL)

    return {
        "token": token,
        "expiresAt": expiresAt,
        "baseUrl": baseUrl,
    }


def deriveCopilotApiBaseUrlFromToken(token: str) -> str:
    return DEFAULT_COPILOT_API_BASE_URL

__all__ = [
    "DEFAULT_COPILOT_API_BASE_URL",
    "resolveCopilotApiToken",
    "deriveCopilotApiBaseUrlFromToken",
]