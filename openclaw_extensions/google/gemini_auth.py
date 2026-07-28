import os
from typing import Optional, Tuple, Dict, Any

from .config_defaults import GoogleConfigDefaults


GEMINI_API_KEY_ENV_VAR = "GOOGLE_API_KEY"
GEMINI_API_KEY_ALT_ENV_VAR = "GOOGLE_GEMINI_API_KEY"
GOOGLE_PROJECT_ID_ENV_VAR = "GOOGLE_CLOUD_PROJECT"
GOOGLE_PROJECT_ID_ALT_ENV_VAR = "GOOGLE_PROJECT_ID"
GOOGLE_CLIENT_ID_ENV_VAR = "GOOGLE_CLIENT_ID"
GOOGLE_CLIENT_SECRET_ENV_VAR = "GOOGLE_CLIENT_SECRET"
GOOGLE_LOCATION_ENV_VAR = "GOOGLE_CLOUD_LOCATION"
GOOGLE_APPLICATION_CREDENTIALS_ENV_VAR = "GOOGLE_APPLICATION_CREDENTIALS"


def parse_gemini_auth(config: Optional[GoogleConfigDefaults] = None) -> Dict[str, Any]:
    api_key = None
    project_id = None
    client_id = None
    client_secret = None

    if config:
        api_key = config.google_api_key
        project_id = config.google_project_id
        client_id = config.google_client_id
        client_secret = config.google_client_secret

    if not api_key:
        api_key = resolve_google_api_key_from_environment()

    if not project_id:
        project_id = resolve_google_project_id_from_environment()

    if not client_id:
        client_id = os.environ.get(GOOGLE_CLIENT_ID_ENV_VAR)

    if not client_secret:
        client_secret = os.environ.get(GOOGLE_CLIENT_SECRET_ENV_VAR)

    return {
        "api_key": api_key,
        "project_id": project_id,
        "client_id": client_id,
        "client_secret": client_secret,
        "auth_type": "api_key" if api_key else "oauth" if client_id and client_secret else "none",
    }


def resolve_google_api_key_from_environment() -> Optional[str]:
    api_key = os.environ.get(GEMINI_API_KEY_ENV_VAR)
    if api_key:
        return api_key
    api_key = os.environ.get(GEMINI_API_KEY_ALT_ENV_VAR)
    if api_key:
        return api_key
    return None


def infer_google_project_id() -> Optional[str]:
    return resolve_google_project_id_from_environment()


def resolve_google_project_id_from_environment() -> Optional[str]:
    project_id = os.environ.get(GOOGLE_PROJECT_ID_ENV_VAR)
    if project_id:
        return project_id
    project_id = os.environ.get(GOOGLE_PROJECT_ID_ALT_ENV_VAR)
    if project_id:
        return project_id
    return resolve_google_project_id_from_gcloud_config()


def resolve_google_project_id_from_gcloud_config() -> Optional[str]:
    gcloud_config_dir = os.path.expanduser("~/.config/gcloud/configurations")
    if not os.path.isdir(gcloud_config_dir):
        return None
    try:
        default_config_path = os.path.join(gcloud_config_dir, "config_default")
        if os.path.isfile(default_config_path):
            with open(default_config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("project = "):
                        return line.split("=", 1)[1].strip()
        active_config_path = os.path.join(gcloud_config_dir, "active_config")
        if os.path.isfile(active_config_path):
            with open(active_config_path, "r") as f:
                for line in f:
                    line = line.strip()
                    if line.startswith("project = "):
                        return line.split("=", 1)[1].strip()
    except (IOError, OSError):
        return None
    return None


def resolve_google_project_id_from_application_default_credentials() -> Optional[str]:
    creds_path = os.environ.get(GOOGLE_APPLICATION_CREDENTIALS_ENV_VAR)
    if creds_path and os.path.isfile(creds_path):
        try:
            import json
            with open(creds_path, "r") as f:
                creds = json.load(f)
                return creds.get("project_id")
        except (IOError, OSError, ValueError, ImportError):
            return None
    default_creds_path = os.path.expanduser(
        "~/.config/gcloud/application_default_credentials.json"
    )
    if os.path.isfile(default_creds_path):
        try:
            import json
            with open(default_creds_path, "r") as f:
                creds = json.load(f)
                return creds.get("project_id")
        except (IOError, OSError, ValueError, ImportError):
            return None
    return None


def resolve_google_location_from_environment() -> Optional[str]:
    location = os.environ.get(GOOGLE_LOCATION_ENV_VAR)
    if location:
        return location
    return None


def resolve_google_generative_ai_http_request_config(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
    timeout: Optional[int] = None,
    config: Optional[GoogleConfigDefaults] = None,
) -> Dict[str, Any]:
    if config:
        if not base_url:
            base_url = config.google_generative_ai_http_base_url
        if not api_key:
            api_key = config.google_api_key
        if not timeout:
            timeout = config.google_generative_ai_http_request_timeout

    if not base_url:
        base_url = os.environ.get(
            "GOOGLE_GENERATIVE_AI_HTTP_BASE_URL",
            "https://generativelanguage.googleapis.com",
        )

    if not timeout:
        timeout = 60000

    headers = {
        "Content-Type": "application/json",
    }

    if api_key:
        params = {"key": api_key}
    else:
        params = {}

    return {
        "base_url": base_url,
        "headers": headers,
        "params": params,
        "timeout": timeout,
    }