import os
import json
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

from .config_defaults import GoogleConfigDefaults


@dataclass
class OAuthSettings:
    client_id: Optional[str] = None
    client_secret: Optional[str] = None
    project_id: Optional[str] = None
    redirect_host: str = "localhost"
    redirect_port: int = 3456
    scopes: list = field(default_factory=lambda: [
        "openid",
        "email",
        "profile",
        "https://www.googleapis.com/auth/cloud-platform",
    ])
    auto_refresh: bool = True
    token_storage_path: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "project_id": self.project_id,
            "redirect_host": self.redirect_host,
            "redirect_port": self.redirect_port,
            "scopes": self.scopes,
            "auto_refresh": self.auto_refresh,
            "token_storage_path": self.token_storage_path,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthSettings":
        return cls(
            client_id=data.get("client_id"),
            client_secret=data.get("client_secret"),
            project_id=data.get("project_id"),
            redirect_host=data.get("redirect_host", "localhost"),
            redirect_port=data.get("redirect_port", 3456),
            scopes=data.get("scopes", [
                "openid",
                "email",
                "profile",
                "https://www.googleapis.com/auth/cloud-platform",
            ]),
            auto_refresh=data.get("auto_refresh", True),
            token_storage_path=data.get("token_storage_path"),
        )


def resolve_oauth_settings(config: Optional[GoogleConfigDefaults] = None) -> OAuthSettings:
    settings = OAuthSettings()

    if config:
        settings.client_id = config.google_client_id
        settings.client_secret = config.google_client_secret
        settings.project_id = config.google_project_id

    if not settings.client_id:
        settings.client_id = os.environ.get("GOOGLE_CLIENT_ID")
    if not settings.client_secret:
        settings.client_secret = os.environ.get("GOOGLE_CLIENT_SECRET")
    if not settings.project_id:
        settings.project_id = os.environ.get("GOOGLE_CLOUD_PROJECT")

    return settings