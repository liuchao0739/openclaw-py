from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import (
    parse_gemini_auth,
    resolve_google_api_key_from_environment,
    resolve_google_project_id_from_environment,
)
from .oauth_shared import validate_oauth_setup, get_oauth_status


class GoogleSetupAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config

    def get_setup_status(self) -> Dict[str, Any]:
        auth = parse_gemini_auth(self.config)
        oauth_status = get_oauth_status(self.config)

        issues = []
        warnings = []

        if auth.get("auth_type") == "none":
            issues.append("No API key or OAuth credentials configured")
        elif auth.get("auth_type") == "oauth":
            validation = validate_oauth_setup(self.config)
            if not validation.get("valid"):
                issues.extend(validation.get("issues", []))

        if not auth.get("project_id"):
            warnings.append("No Google Cloud project ID configured")

        return {
            "is_configured": auth.get("auth_type") != "none",
            "auth_type": auth.get("auth_type"),
            "has_api_key": bool(auth.get("api_key")),
            "has_oauth": bool(auth.get("client_id") and auth.get("client_secret")),
            "has_project_id": bool(auth.get("project_id")),
            "oauth_status": oauth_status,
            "issues": issues,
            "warnings": warnings,
        }

    def validate_setup(self) -> Dict[str, Any]:
        status = self.get_setup_status()
        issues = status.get("issues", [])
        return {
            "valid": len(issues) == 0,
            "issues": issues,
            "warnings": status.get("warnings", []),
            "status": status,
        }

    def get_required_steps(self) -> List[Dict[str, Any]]:
        steps = []
        status = self.get_setup_status()

        if not status.get("has_api_key"):
            steps.append({
                "step": 1,
                "title": "Set up API key",
                "description": "Create a Google API key and set it in your environment",
                "command": "export GOOGLE_API_KEY=your_api_key",
                "completed": False,
            })

        if not status.get("has_project_id"):
            steps.append({
                "step": 2,
                "title": "Set up project ID",
                "description": "Set your Google Cloud project ID",
                "command": "export GOOGLE_CLOUD_PROJECT=your_project_id",
                "completed": False,
            })

        return steps

    def get_environment_variables(self) -> Dict[str, Any]:
        return {
            "GOOGLE_API_KEY": resolve_google_api_key_from_environment(),
            "GOOGLE_CLOUD_PROJECT": resolve_google_project_id_from_environment(),
            "GOOGLE_CLIENT_ID": None,
            "GOOGLE_CLIENT_SECRET": None,
        }