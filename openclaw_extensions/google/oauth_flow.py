import os
import json
import secrets
import hashlib
import base64
import time
from typing import Optional, Dict, Any, Tuple, Callable
from urllib.parse import urlencode, urlparse, parse_qs

from .oauth_credentials import resolve_oauth_client_id, resolve_oauth_client_secret
from .config_defaults import GoogleConfigDefaults

OAUTH2_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH2_TOKEN_URL = "https://oauth2.googleapis.com/token"
DEFAULT_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/cloud-platform",
]
DEFAULT_REDIRECT_HOST = "localhost"
DEFAULT_REDIRECT_PORT = 3456


class OAuthFlow:
    def __init__(
        self,
        client_id: str,
        client_secret: str,
        redirect_uri: Optional[str] = None,
        scopes: Optional[list] = None,
    ):
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri or f"http://{DEFAULT_REDIRECT_HOST}:{DEFAULT_REDIRECT_PORT}"
        self.scopes = scopes or DEFAULT_SCOPES
        self._state = None
        self._code_verifier = None
        self._code_challenge = None

    def generate_auth_url(self) -> str:
        self._state = secrets.token_urlsafe(16)
        self._code_verifier = secrets.token_urlsafe(32)
        self._code_challenge = self._compute_code_challenge(self._code_verifier)

        params = {
            "client_id": self.client_id,
            "redirect_uri": self.redirect_uri,
            "response_type": "code",
            "scope": " ".join(self.scopes),
            "state": self._state,
            "code_challenge": self._code_challenge,
            "code_challenge_method": "S256",
            "access_type": "offline",
            "prompt": "consent",
        }
        return f"{OAUTH2_AUTH_URL}?{urlencode(params)}"

    @staticmethod
    def _compute_code_challenge(code_verifier: str) -> str:
        digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
        return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")

    def exchange_code(self, code: str, state: Optional[str] = None) -> Optional[Dict[str, Any]]:
        if state and state != self._state:
            return None
        import urllib.request
        import urllib.error

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "code": code,
            "redirect_uri": self.redirect_uri,
            "grant_type": "authorization_code",
        }
        if self._code_verifier:
            data["code_verifier"] = self._code_verifier

        try:
            req = urllib.request.Request(
                OAUTH2_TOKEN_URL,
                data=urlencode(data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None

    def refresh_token(self, refresh_token: str) -> Optional[Dict[str, Any]]:
        import urllib.request
        import urllib.error

        data = {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "refresh_token": refresh_token,
            "grant_type": "refresh_token",
        }
        try:
            req = urllib.request.Request(
                OAUTH2_TOKEN_URL,
                data=urlencode(data).encode("utf-8"),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except (urllib.error.URLError, urllib.error.HTTPError, ValueError):
            return None

    @staticmethod
    def extract_code_from_url(url: str) -> Tuple[Optional[str], Optional[str]]:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        return params.get("code", [None])[0], params.get("state", [None])[0]


def create_oauth_flow(config: Optional[GoogleConfigDefaults] = None) -> Optional[OAuthFlow]:
    client_id = resolve_oauth_client_id(config)
    client_secret = resolve_oauth_client_secret(config)
    if not client_id or not client_secret:
        return None
    return OAuthFlow(client_id=client_id, client_secret=client_secret)