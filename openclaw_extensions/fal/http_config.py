from typing import Dict, Optional


FAL_BASE_URL = "https://fal.run"
FAL_QUEUE_BASE_URL = "https://queue.fal.run"


def resolve_fal_http_request_config(req: Dict, capability: str = "image") -> Dict:
    env_vars = req.get("env", {})
    api_key = env_vars.get("FAL_API_KEY") or env_vars.get("FAL_KEY")
    
    headers = {
        "Content-Type": "application/json",
    }
    if api_key:
        headers["Authorization"] = f"Key {api_key}"
    
    return {
        "baseUrl": FAL_BASE_URL,
        "allowPrivateNetwork": False,
        "headers": headers,
        "dispatcherPolicy": None,
    }