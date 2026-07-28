import os
import json
from typing import Optional, Dict, Any

from .config_defaults import GoogleConfigDefaults


CLI_AUTH_HOME_DIR = os.path.expanduser("~/.openclaw/google/cli-auth")


def _ensure_cli_auth_home() -> str:
    os.makedirs(CLI_AUTH_HOME_DIR, exist_ok=True)
    return CLI_AUTH_HOME_DIR


def get_cli_auth_home_dir() -> str:
    return _ensure_cli_auth_home()


def get_cli_auth_config_path() -> str:
    return os.path.join(CLI_AUTH_HOME_DIR, "config.json")


def get_cli_auth_token_path() -> str:
    return os.path.join(CLI_AUTH_HOME_DIR, "token.json")


def load_cli_auth_config() -> Optional[Dict[str, Any]]:
    path = get_cli_auth_config_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return None


def save_cli_auth_config(config: Dict[str, Any]) -> None:
    os.makedirs(CLI_AUTH_HOME_DIR, exist_ok=True)
    path = get_cli_auth_config_path()
    with open(path, "w") as f:
        json.dump(config, f, indent=2)


def load_cli_auth_token() -> Optional[Dict[str, Any]]:
    path = get_cli_auth_token_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            return json.load(f)
    except (IOError, OSError, ValueError):
        return None


def save_cli_auth_token(token: Dict[str, Any]) -> None:
    os.makedirs(CLI_AUTH_HOME_DIR, exist_ok=True)
    path = get_cli_auth_token_path()
    with open(path, "w") as f:
        json.dump(token, f, indent=2)


def delete_cli_auth_token() -> bool:
    path = get_cli_auth_token_path()
    if os.path.isfile(path):
        os.remove(path)
        return True
    return False


def get_cli_auth_status() -> Dict[str, Any]:
    config = load_cli_auth_config()
    token = load_cli_auth_token()
    return {
        "has_config": bool(config),
        "has_token": bool(token),
        "is_authenticated": bool(config and token),
        "config_path": get_cli_auth_config_path(),
        "token_path": get_cli_auth_token_path(),
    }


def resolve_cli_auth_config(
    config: Optional[GoogleConfigDefaults] = None,
) -> Dict[str, Any]:
    cli_config = load_cli_auth_config()
    if cli_config:
        return cli_config

    if config:
        return {
            "client_id": config.google_client_id,
            "client_secret": config.google_client_secret,
            "project_id": config.google_project_id,
        }

    return {}