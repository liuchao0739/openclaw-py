import os
import json
import time
from typing import Optional, Dict, Any, List

from .oauth_token import OAuthToken, load_token, save_token, delete_token
from .oauth_settings import OAuthSettings, resolve_oauth_settings
from .config_defaults import GoogleConfigDefaults


OAUTH_SETTINGS_PATH = os.path.expanduser("~/.openclaw/google/oauth_settings.json")


def load_oauth_settings() -> Optional[OAuthSettings]:
    if not os.path.isfile(OAUTH_SETTINGS_PATH):
        return None
    try:
        with open(OAUTH_SETTINGS_PATH, "r") as f:
            data = json.load(f)
            return OAuthSettings.from_dict(data)
    except (IOError, OSError, ValueError):
        return None


def save_oauth_settings(settings: OAuthSettings) -> None:
    os.makedirs(os.path.dirname(OAUTH_SETTINGS_PATH), exist_ok=True)
    with open(OAUTH_SETTINGS_PATH, "w") as f:
        json.dump(settings.to_dict(), f, indent=2)


def clear_oauth_settings() -> bool:
    if os.path.isfile(OAUTH_SETTINGS_PATH):
        os.remove(OAUTH_SETTINGS_PATH)
        return True
    return False


def get_oauth_status(config: Optional[GoogleConfigDefaults] = None) -> Dict[str, Any]:
    settings = load_oauth_settings()
    if not settings:
        settings = resolve_oauth_settings(config)

    token = load_token()

    return {
        "has_credentials": bool(settings.client_id and settings.client_secret),
        "has_token": bool(token),
        "token_valid": bool(token and token.is_valid()),
        "token_expired": bool(token and token.is_expired()),
        "has_project_id": bool(settings.project_id),
        "client_id_configured": bool(settings.client_id),
        "project_id": settings.project_id,
    }


def validate_oauth_setup(config: Optional[GoogleConfigDefaults] = None) -> Dict[str, Any]:
    status = get_oauth_status(config)
    issues = []

    if not status["client_id_configured"]:
        issues.append("Client ID is not configured")
    if not status["has_token"]:
        issues.append("Not authenticated - please run login")
    elif status["token_expired"]:
        issues.append("Token has expired - please run login again")

    return {
        "valid": len(issues) == 0,
        "issues": issues,
        "status": status,
    }