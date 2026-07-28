import os
import json
from typing import Optional, Dict, Any

from .config_defaults import GoogleConfigDefaults

PROJECT_CONFIG_DIR = os.path.expanduser("~/.openclaw/google")
PROJECT_CONFIG_FILE = "project_config.json"


def _get_project_config_path() -> str:
    os.makedirs(PROJECT_CONFIG_DIR, exist_ok=True)
    return os.path.join(PROJECT_CONFIG_DIR, PROJECT_CONFIG_FILE)


def get_configured_project_id() -> Optional[str]:
    path = _get_project_config_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("project_id")
    except (IOError, OSError, ValueError):
        return None


def set_configured_project_id(project_id: str) -> None:
    path = _get_project_config_path()
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (IOError, OSError, ValueError):
            pass
    data["project_id"] = project_id
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def get_configured_location() -> Optional[str]:
    path = _get_project_config_path()
    if not os.path.isfile(path):
        return None
    try:
        with open(path, "r") as f:
            data = json.load(f)
            return data.get("location", "us-central1")
    except (IOError, OSError, ValueError):
        return None


def set_configured_location(location: str) -> None:
    path = _get_project_config_path()
    data = {}
    if os.path.isfile(path):
        try:
            with open(path, "r") as f:
                data = json.load(f)
        except (IOError, OSError, ValueError):
            pass
    data["location"] = location
    with open(path, "w") as f:
        json.dump(data, f, indent=2)


def resolve_project_id(config: Optional[GoogleConfigDefaults] = None) -> Optional[str]:
    if config and config.google_project_id:
        return config.google_project_id
    configured = get_configured_project_id()
    if configured:
        return configured
    env_project = os.environ.get("GOOGLE_CLOUD_PROJECT")
    if env_project:
        return env_project
    env_project_alt = os.environ.get("GOOGLE_PROJECT_ID")
    if env_project_alt:
        return env_project_alt
    return None


def resolve_location(config: Optional[GoogleConfigDefaults] = None) -> str:
    if config and config.google_vertex_ai_location:
        return config.google_vertex_ai_location
    configured = get_configured_location()
    if configured:
        return configured
    env_location = os.environ.get("GOOGLE_CLOUD_LOCATION")
    if env_location:
        return env_location
    return "us-central1"