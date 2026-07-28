import os
import json
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import parse_gemini_auth


class GoogleOnboard:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config

    def get_onboarding_steps(self) -> List[Dict[str, Any]]:
        auth = parse_gemini_auth(self.config)

        steps = [
            {
                "step": 1,
                "title": "Install the Google Cloud SDK",
                "description": "Download and install the Google Cloud SDK",
                "completed": self._is_gcloud_installed(),
                "action": "https://cloud.google.com/sdk/docs/install",
            },
            {
                "step": 2,
                "title": "Authenticate with Google Cloud",
                "description": "Run gcloud auth login to authenticate",
                "completed": bool(auth.get("api_key") or auth.get("client_id")),
                "action": "gcloud auth login",
            },
            {
                "step": 3,
                "title": "Set project ID",
                "description": "Set your Google Cloud project ID",
                "completed": bool(auth.get("project_id")),
                "action": "gcloud config set project YOUR_PROJECT_ID",
            },
            {
                "step": 4,
                "title": "Enable required APIs",
                "description": "Enable the Generative AI and other required APIs",
                "completed": False,
                "action": "gcloud services enable generativeai.googleapis.com",
            },
            {
                "step": 5,
                "title": "Create API key",
                "description": "Create an API key for authentication",
                "completed": bool(auth.get("api_key")),
                "action": "https://console.cloud.google.com/apis/credentials",
            },
        ]

        return steps

    def _is_gcloud_installed(self) -> bool:
        import shutil
        return shutil.which("gcloud") is not None

    def get_onboarding_status(self) -> Dict[str, Any]:
        steps = self.get_onboarding_steps()
        completed = sum(1 for s in steps if s.get("completed"))
        return {
            "total_steps": len(steps),
            "completed_steps": completed,
            "progress": f"{completed}/{len(steps)}",
            "is_complete": completed == len(steps),
            "steps": steps,
        }

    def generate_setup_commands(self) -> List[str]:
        commands = []
        steps = self.get_onboarding_steps()

        for step in steps:
            if not step.get("completed"):
                action = step.get("action", "")
                if action and not action.startswith("http"):
                    commands.append(action)

        return commands

    def get_required_env_vars(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "GOOGLE_API_KEY",
                "description": "Google API key for authentication",
                "required": True,
                "current_value": os.environ.get("GOOGLE_API_KEY"),
            },
            {
                "name": "GOOGLE_CLOUD_PROJECT",
                "description": "Google Cloud project ID",
                "required": False,
                "current_value": os.environ.get("GOOGLE_CLOUD_PROJECT"),
            },
            {
                "name": "GOOGLE_CLOUD_LOCATION",
                "description": "Google Cloud region/location",
                "required": False,
                "current_value": os.environ.get("GOOGLE_CLOUD_LOCATION"),
            },
        ]