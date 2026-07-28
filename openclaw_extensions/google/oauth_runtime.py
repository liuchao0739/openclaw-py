import os
import json
import time
from typing import Optional, Dict, Any

from .oauth_token import OAuthToken, load_token, save_token
from .oauth_flow import create_oauth_flow
from .oauth_project import resolve_project_id, resolve_location
from .config_defaults import GoogleConfigDefaults


class OAuthRuntime:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._token: Optional[OAuthToken] = None
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._token = load_token()
        self._initialized = True

    def get_access_token(self) -> Optional[str]:
        self.initialize()
        if not self._token:
            return None
        if self._token.is_expired():
            self._refresh_token()
        return self._token.access_token if self._token else None

    def _refresh_token(self) -> None:
        if not self._token or not self._token.refresh_token:
            return
        flow = create_oauth_flow(self.config)
        if not flow:
            return
        response = flow.refresh_token(self._token.refresh_token)
        if response:
            new_token = OAuthToken.from_response(response)
            if new_token.refresh_token is None:
                new_token.refresh_token = self._token.refresh_token
            self._token = new_token
            save_token(new_token)

    def get_headers(self) -> Dict[str, str]:
        token = self.get_access_token()
        if token:
            return {"Authorization": f"Bearer {token}"}
        return {}

    def is_authenticated(self) -> bool:
        self.initialize()
        return bool(self._token and self._token.is_valid())

    def clear(self) -> None:
        self._token = None
        self._initialized = False

    def get_project_id(self) -> Optional[str]:
        return resolve_project_id(self.config)

    def get_location(self) -> str:
        return resolve_location(self.config)