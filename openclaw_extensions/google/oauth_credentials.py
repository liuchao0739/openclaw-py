import os
import json
from typing import Optional, Dict, Any

from .config_defaults import GoogleConfigDefaults

GOOGLE_CLIENT_ID_ENV_VAR = "GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET_ENV_VAR = "GOOGLE_CLIENT_SECRET"

DEFAULT_CLIENT_ID = ""
DEFAULT_CLIENT_SECRET = ""


def resolve_oauth_client_id(config: Optional[GoogleConfigDefaults] = None) -> Optional[str]:
    if config and config.google_client_id:
        return config.google_client_id
    return os.environ.get(GOOGLE_CLIENT_ID_ENV_VAR)


def resolve_oauth_client_secret(config: Optional[GoogleConfigDefaults] = None) -> Optional[str]:
    if config and config.google_client_secret:
        return config.google_client_secret
    return os.environ.get(GOOGLE_CLIENT_SECRET_ENV_VAR)


def has_oauth_credentials(config: Optional[GoogleConfigDefaults] = None) -> bool:
    return bool(
        resolve_oauth_client_id(config) and resolve_oauth_client_secret(config)
    )


def get_oauth_credentials_path() -> str:
    home = os.path.expanduser("~")
    return os.path.join(home, ".openclaw", "google", "oauth_credentials.json")


def save_oauth_credentials(client_id: str, client_secret: str) -> None:
    creds_dir = os.path.dirname(get_oauth_credentials_path())
    os.makedirs(creds_dir, exist_ok=True)
    creds = {
        "client_id": client_id,
        "client_secret": client_secret,
    }
    with open(get_oauth_credentials_path(), "w") as f:
        json.dump(creds, f, indent=2)


def load_oauth_credentials() -> Optional[Dict[str, str]]:
    path = get_oauth_credentials_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return None


def delete_oauth_credentials() -> bool:
    path = get_oauth_credentials_path()
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False