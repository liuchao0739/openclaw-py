import os
import json
import time
from typing import Optional, Dict, Any
from dataclasses import dataclass, field

TOKEN_STORAGE_DIR = os.path.expanduser("~/.openclaw/google/tokens")


@dataclass
class OAuthToken:
    access_token: str = ""
    refresh_token: Optional[str] = None
    token_type: str = "Bearer"
    expires_at: Optional[int] = None
    scope: Optional[str] = None
    id_token: Optional[str] = None

    def is_expired(self, margin_seconds: int = 60) -> bool:
        if not self.expires_at:
            return True
        return time.time() >= (self.expires_at - margin_seconds)

    def is_valid(self) -> bool:
        return bool(self.access_token and not self.is_expired())

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "access_token": self.access_token,
            "token_type": self.token_type,
        }
        if self.refresh_token:
            result["refresh_token"] = self.refresh_token
        if self.expires_at:
            result["expires_at"] = self.expires_at
        if self.scope:
            result["scope"] = self.scope
        if self.id_token:
            result["id_token"] = self.id_token
        return result

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "OAuthToken":
        return cls(
            access_token=data.get("access_token", ""),
            refresh_token=data.get("refresh_token"),
            token_type=data.get("token_type", "Bearer"),
            expires_at=data.get("expires_at"),
            scope=data.get("scope"),
            id_token=data.get("id_token"),
        )

    @classmethod
    def from_response(cls, response_data: Dict[str, Any]) -> "OAuthToken":
        expires_in = response_data.get("expires_in", 3600)
        return cls(
            access_token=response_data.get("access_token", ""),
            refresh_token=response_data.get("refresh_token"),
            token_type=response_data.get("token_type", "Bearer"),
            expires_at=time.time() + expires_in,
            scope=response_data.get("scope"),
            id_token=response_data.get("id_token"),
        )


def _get_storage_dir() -> str:
    os.makedirs(TOKEN_STORAGE_DIR, exist_ok=True)
    return TOKEN_STORAGE_DIR


def save_token(token: OAuthToken, account_id: str = "default") -> None:
    storage_dir = _get_storage_dir()
    token_file = os.path.join(storage_dir, f"token_{account_id}.json")
    with open(token_file, "w") as f:
        json.dump(token.to_dict(), f, indent=2)


def load_token(account_id: str = "default") -> Optional[OAuthToken]:
    storage_dir = _get_storage_dir()
    token_file = os.path.join(storage_dir, f"token_{account_id}.json")
    if not os.path.isfile(token_file):
        return None
    try:
        with open(token_file, "r") as f:
            data = json.load(f)
            return OAuthToken.from_dict(data)
    except (IOError, OSError, ValueError):
        return None


def delete_token(account_id: str = "default") -> bool:
    storage_dir = _get_storage_dir()
    token_file = os.path.join(storage_dir, f"token_{account_id}.json")
    if os.path.isfile(token_file):
        os.remove(token_file)
        return True
    return False


def list_stored_accounts() -> list:
    storage_dir = _get_storage_dir()
    accounts = []
    for filename in os.listdir(storage_dir):
        if filename.startswith("token_") and filename.endswith(".json"):
            account_id = filename[len("token_"):-len(".json")]
            accounts.append(account_id)
    return accounts