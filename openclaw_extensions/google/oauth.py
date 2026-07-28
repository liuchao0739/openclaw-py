import os
import json
import hashlib
import secrets
import base64
import time
from typing import Optional, Dict, Any, Tuple
from urllib.parse import urlencode, urlparse, parse_qs

from .config_defaults import GoogleConfigDefaults


OAUTH2_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
OAUTH2_TOKEN_URL = "https://oauth2.googleapis.com/token"
OAUTH2_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
OAUTH2_USER_INFO_URL = "https://www.googleapis.com/oauth2/v2/userinfo"

DEFAULT_OAUTH_REDIRECT_PORT = 3456
DEFAULT_OAUTH_REDIRECT_HOST = "localhost"
DEFAULT_OAUTH_SCOPES = [
    "openid",
    "email",
    "profile",
    "https://www.googleapis.com/auth/cloud-platform",
]

TOKEN_STORAGE_DIR = os.path.expanduser("~/.openclaw/google/tokens")


@dataclass
class OAuthToken:
    access_token: str = ""
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[int] = None
    scope: Optional[str] = None

    def is_expired(self) -> bool:
        if not self.expires_at:
            return True
        return time.time() >= self.expires_at

    def to_dict(self) -> Dict[str, Any]:
        return {
            "access_token": self.access_token,
            "refresh_token": self.refresh_token,
            "token_type": self.token_type,
            "expires_at": self.expires_at,
            "scope": self.scope,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthToken":
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_at"),
            scope=data.get("scope"),
        )


@dataclass
class OAuthCredentials:
    client_id: str = ""
    client_secret: str = ""
    project_id: Optional[str] = None
    auth_uri: str = OAUTH2_AUTH_URL
    token_uri: str = OAUTH2_TOKEN_URL
    revoke_uri: str = OAUTH2_REVOKE_URL

    def to_dict(self) -> Dict[str, Any]:
        return {
            "client_id": self.client_id,
            "client_secret": self.client_secret,
            "project_id": self.project_id,
            "auth_uri": self.auth_uri,
            "token_uri": self.token_uri,
            "revoke_uri": self.revoke_uri,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthCredentials":
        return cls(
            client_id=data.get("client_id", ""),
            client_secret=data.get("client_secret", ""),
            project_id=data.get("project_id"),
            auth_uri=data.get("auth_uri", OAUTH2_AUTH_URL),
            token_uri=data.get("token_uri", OAUTH2_TOKEN_URL),
            revoke_uri=data.get("revoke_uri", OAUTH2_REVOKE_URL),
        )


@dataclass
class OAuthFlowConfig:
    redirect_uri: str = f"http://{DEFAULT_OAUTH_REDIRECT_HOST}:{DEFAULT_OAUTH_REDIRECT_PORT}"
    scopes: list = field(default_factory=lambda: list(DEFAULT_OAUTH_SCOPES))
    state: Optional[str] = None
    code_challenge: Optional[str] = None
    code_challenge_method: str = "S256"
    response_type: str = "code"
    access_type: str = "offline"
    prompt: str = "consent"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "redirect_uri": self.redirect_uri,
            "scopes": self.scopes,
            "state": self.state,
            "code_challenge": self.code_challenge,
            "code_challenge_method": self.code_challenge_method,
            "response_type": self.response_type,
            "access_type": self.access_type,
            "prompt": self.prompt,
        }


def _generate_code_verifier() -> str:
    return secrets.token_urlsafe(32)


def _generate_code_challenge(code_verifier: str) -> str:
    digest = hashlib.sha256(code_verifier.encode("ascii")).digest()
    return base64.urlsafe_b64encode(digest).decode("ascii").rstrip("=")


def _generate_state() -> str:
    return secrets.token_urlsafe(16)


def build_oauth_auth_url(
    credentials: OAuthCredentials,
    flow_config: OAuthFlowConfig,
) -> str:
    params = {
        "client_id": credentials.client_id,
        "redirect_uri": flow_config.redirect_uri,
        "response_type": flow_config.response_type,
        "scope": " ".join(flow_config.scopes),
        "access_type": flow_config.access_type,
        "prompt": flow_config.prompt,
    }

    if flow_config.state:
        params["state"] = flow_config.state

    if flow_config.code_challenge:
        params["code_challenge"] = flow_config.code_challenge
        params["code_challenge_method"] = flow_config.code_challenge_method

    return f"{OAUTH2_AUTH_URL}?{urlencode(params)}"


def extract_code_from_redirect_url(redirect_url: str) -> Tuple[Optional[str], Optional[str]]:
    parsed = urlparse(redirect_url)
    params = parse_qs(parsed.query)
    code = params.get("code", [None])[0]
    state = params.get("state", [None])[0]
    return code, state


def exchange_code_for_token(
    credentials: OAuthCredentials,
    code: str,
    redirect_uri: str,
    code_verifier: Optional[str] = None,
) -> Optional[OAuthToken]:
    import urllib.request
    import urllib.error

    data = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
        "code": code,
        "redirect_uri": redirect_uri,
        "grant_type": "authorization_code",
    }

    if code_verifier:
        data["code_verifier"] = code_verifier

    try:
        req = urllib.request.Request(
            OAUTH2_TOKEN_URL,
            data=urlencode(data).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        with urllib.request.urlopen(req, timeout=30) as resp:
            response_data = json.loads(resp.read().decode("utf-8"))
            return OAuthToken(
                access_token=response_data.get("access_token", ""),
                refresh_token=response_data.get("refresh_token"),
                token_type=response_data.get("token_type", "Bearer"),
                expires_at=time.time() + response_data.get("expires_in", 3600),
                scope=response_data.get("scope"),
            )
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError):
        return None


def refresh_oauth_token(
    credentials: OAuthCredentials,
    refresh_token: str,
) -> Optional[OAuthToken]:
    import urllib.request
    import urllib.error

    data = {
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
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
            response_data = json.loads(resp.read().decode("utf-8"))
            return OAuthToken(
                access_token=response_data.get("access_token", ""),
                refresh_token=response_data.get("refresh_token", refresh_token),
                token_type=response_data.get("token_type", "Bearer"),
                expires_at=time.time() + response_data.get("expires_in", 3600),
                scope=response_data.get("scope"),
            )
    except (urllib.error.URLError, urllib.error.HTTPError, ValueError, KeyError):
        return None


def revoke_oauth_token(
    credentials: OAuthCredentials,
    token: str,
) -> bool:
    import urllib.request
    import urllib.error

    data = {
        "token": token,
        "client_id": credentials.client_id,
        "client_secret": credentials.client_secret,
    }

    try:
        req = urllib.request.Request(
            OAUTH2_REVOKE_URL,
            data=urlencode(data).encode("utf-8"),
            headers={"Content-Type": "application/x-www-form-urlencoded"},
        )
        urllib.request.urlopen(req, timeout=30)
        return True
    except (urllib.error.URLError, urllib.error.HTTPError):
        return False


def get_or_create_token_storage_path() -> str:
    os.makedirs(TOKEN_STORAGE_DIR, exist_ok=True)
    return TOKEN_STORAGE_DIR


def save_oauth_token(token: OAuthToken, provider: str = "google") -> None:
    storage_path = get_or_create_token_storage_path()
    token_file = os.path.join(storage_path, f"{provider}_token.json")
    with open(token_file, "w") as f:
        json.dump(token.to_dict(), f, indent=2)


def load_oauth_token(provider: str = "google") -> Optional[OAuthToken]:
    storage_path = get_or_create_token_storage_path()
    token_file = os.path.join(storage_path, f"{provider}_token.json")
    if not os.path.isfile(token_file):
        return None
    try:
        with open(token_file, "r") as f:
            data = json.load(f)
            return OAuthToken.from_dict(data)
    except (IOError, OSError, ValueError):
        return None


def delete_oauth_token(provider: str = "google") -> bool:
    storage_path = get_or_create_token_storage_path()
    token_file = os.path.join(storage_path, f"{provider}_token.json")
    if os.path.isfile(token_file):
        os.remove(token_file)
        return True
    return False


def resolve_oauth_credentials(config: Optional[GoogleConfigDefaults] = None) -> Optional[OAuthCredentials]:
    client_id = None
    client_secret = None
    project_id = None

    if config:
        client_id = config.google_client_id
        client_secret = config.google_client_secret
        project_id = config.google_project_id

    if not client_id:
        client_id = os.environ.get(GOOGLE_CLIENT_ID_ENV_VAR)
    if not client_secret:
        client_secret = os.environ.get(GOOGLE_CLIENT_SECRET_ENV_VAR)
    if not project_id:
        project_id = os.environ.get(GOOGLE_PROJECT_ID_ENV_VAR)

    if not client_id or not client_secret:
        return None

    return OAuthCredentials(
        client_id=client_id,
        client_secret=client_secret,
        project_id=project_id,
    )


from dataclasses import dataclass, field