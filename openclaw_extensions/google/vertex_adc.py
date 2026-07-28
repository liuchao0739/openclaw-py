import os
import json
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults


VERTEX_AI_SERVICE_NAME = "aiplatform"
VERTEX_AI_SERVICE_VERSION = "v1beta1"
VERTEX_AI_DEFAULT_LOCATION = "us-central1"


class VertexADC:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._project_id: Optional[str] = None
        self._location: str = VERTEX_AI_DEFAULT_LOCATION

    def resolve_project_id(self) -> Optional[str]:
        if self.config and self.config.google_vertex_ai_project_override:
            return self.config.google_vertex_ai_project_override
        if self.config and self.config.google_project_id:
            return self.config.google_project_id
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")
        if project_id:
            return project_id
        project_id = os.environ.get("GOOGLE_PROJECT_ID")
        if project_id:
            return project_id
        return None

    def resolve_location(self) -> str:
        if self.config and self.config.google_vertex_ai_location:
            return self.config.google_vertex_ai_location
        location = os.environ.get("GOOGLE_CLOUD_LOCATION")
        if location:
            return location
        return VERTEX_AI_DEFAULT_LOCATION

    def build_vertex_endpoint(self, model_id: str) -> str:
        project_id = self.resolve_project_id()
        location = self.resolve_location()
        base_url = "https://googleapis.com"
        service_name = VERTEX_AI_SERVICE_NAME
        service_version = VERTEX_AI_SERVICE_VERSION

        path = model_id
        if path.startswith("vertex/"):
            path = path[len("vertex/"):]

        return f"{base_url}/{service_name}/{service_version}/projects/{project_id}/locations/{location}/models/{path}"

    def build_vertex_ai_endpoint(self, model_id: str) -> str:
        project_id = self.resolve_project_id()
        location = self.resolve_location()
        base_url = "https://googleapis.com"
        service_name = VERTEX_AI_SERVICE_NAME
        service_version = VERTEX_AI_SERVICE_VERSION

        path = model_id
        if path.startswith("vertex/"):
            path = path[len("vertex/"):]

        return f"{base_url}/{service_name}/{service_version}/projects/{project_id}/locations/{location}/models/{path}"

    def get_vertex_config(self) -> Dict[str, Any]:
        return {
            "project_id": self.resolve_project_id(),
            "location": self.resolve_location(),
            "service_name": VERTEX_AI_SERVICE_NAME,
            "service_version": VERTEX_AI_SERVICE_VERSION,
            "base_url": "https://googleapis.com",
        }

    def is_vertex_configured(self) -> bool:
        return bool(self.resolve_project_id())


def create_vertex_adc(config: Optional[GoogleConfigDefaults] = None) -> VertexADC:
    return VertexADC(config=config)