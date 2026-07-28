import os
import json
import time
from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .gemini_cli_auth_home import (
    load_cli_auth_config,
    load_cli_auth_token,
    save_cli_auth_token,
    get_cli_auth_status,
    resolve_cli_auth_config,
)


class GeminiCliOAuthContext:
    def __init__(
        self,
        client_id: str = "",
        client_secret: str = "",
        project_id: Optional[str] = None,
        access_token: Optional[str] = None,
        refresh_token: Optional[str] = None,
        expires_at: Optional[float] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.project_id = project_id
        self.access_token = access_token
        self.refresh_token = refresh_token
        self.expires_at = expires_at

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        return time.time() >= self.expires_at

    def is_valid(self) -> bool:
        return bool(self.access_token and not self.is_expired())

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "project_id": self.project_id,
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "expires_at": self.expires_at,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "GeminiCliOAuthContext":
        return cls(
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            project_id=data.get("project_id"),
            access_token=data.get("access_token"),
            refresh_token=data.get("refresh_token"),
            expires_at=data.get("expires_at"),
        )


class GeminiCliProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._context: Optional[GeminiCliOAuthContext] = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        cli_config = resolve_cli_auth_config(self.config)
        token = load_cli_auth_token()

        self._context = GeminiCliOAuthContext(
            client_id=cli_config.get("client_id", ""),
            client_secret=cli_config.get("client_secret", ""),
            project_id=cli_config.get("project_id"),
            access_token=token.get("access_token") if token else None,
            refresh_token=token.get("refresh_token") if token else None,
            expires_at=token.get("expires_at") if token else None,
        )
        self._initialized = True

    def get_context(self) -> Optional[GeminiCliOAuthContext]:
        self.initialize()
        return self._context

    def is_authenticated(self) -> bool:
        self.initialize()
        return bool(self._context and self._context.is_valid())

    def get_access_token(self) -> Optional[str]:
        self.initialize()
        if self._context and self._context.is_expired() and self._context.refresh_token:
            self._refresh_token()
        return self._context.access_token if self._context else None

    def _refresh_token(self) -> None:
        if not self._context or not self._context.refresh_token:
            return

        import urllib.request
        import urllib.error

        data = {
            "client_id": self._context.client_id,
            "client_secret": self._context.client_secret,
            "refresh_token": self._context.refresh_token,
            "grant_type": "refresh_token",
        }

        try:
            req = urllib.request.Request(
                "https://oauth2.googleapis.com/token",
                data=urllib.parse.urlencode(data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                response = json.loads(resp.read().decode("utf-8"))
                self._context.access_token = response.get("access_token", "")
                self._context.expires_at = time.time() + response.get("expires_in", 3600)
                if response.get("refresh_token"):
                    self._context.refresh_token = response["refresh_token"]
                save_cli_auth_token({
                    "access_token": self._context.access_token,
                    "refresh_token": self._context.refresh_token,
                    "expires_at": self._context.expires_at,
                })
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            pass

    def get_headers(self) -> Dict[str, str]:
        token = self.get_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def get_status(self) -> Dict[str, Any]:
        self.initialize()
        return {
            "is_authenticated": self.is_authenticated(),
            "has_client_id": bool(self._context and self._context.client_id),
            "has_project_id": bool(self._context and self._context.project_id),
            "token_expired": bool(self._context and self._context.is_expired()),
        }


def build_google_gemini_cli_backend(config: Optional[GoogleConfigDefaults] = None) -> GeminiCliProvider:
    return GeminiCliProvider(config=config)


def register_google_gemini_cli_provider(config: Optional[GoogleConfigDefaults] = None) -> GeminiCliProvider:
    return build_google_gemini_cli_backend(config=config)