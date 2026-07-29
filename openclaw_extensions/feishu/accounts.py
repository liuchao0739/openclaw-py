import os
from typing import Any, Optional

from .types import (
    FeishuConfig,
    FeishuDomain,
    FeishuDefaultAccountSelectionSource,
    ResolvedFeishuAccount,
)

DEFAULT_ACCOUNT_ID = "default"


def _normalize_string(value: Any) -> Optional[str]:
    if isinstance(value, str):
        cleaned = value.strip()
        return cleaned or None
    return None


def _normalize_account_id(account_id: Optional[str]) -> str:
    if not isinstance(account_id, str):
        return DEFAULT_ACCOUNT_ID
    cleaned = account_id.strip()
    return cleaned or DEFAULT_ACCOUNT_ID


def _normalize_optional_account_id(account_id: Any) -> Optional[str]:
    if not isinstance(account_id, str):
        return None
    cleaned = account_id.strip()
    return cleaned or None


def _has_configured_account_value(value: Any) -> bool:
    return bool(_normalize_string(value))


def _coerce_secret_ref(value: Any) -> Optional[dict]:
    if isinstance(value, dict) and value.get("source") in ("env", "file", "exec"):
        source = value.get("source")
        provider = value.get("provider")
        ref_id = value.get("id")
        if isinstance(source, str) and isinstance(provider, str) and isinstance(ref_id, str):
            return {"source": source, "provider": provider, "id": ref_id}
    return None


class FeishuSecretRefUnavailableError(Exception):
    def __init__(self, path: str, ref: dict) -> None:
        self.path = path
        self.ref = ref
        super().__init__(
            f'{path}: unresolved SecretRef "{ref.get("source")}:{ref.get("provider")}:{ref.get("id")}". '
            "Resolve this command against an active gateway runtime snapshot before reading it."
        )


def _resolve_feishu_secret_like(params: dict) -> Optional[str]:
    as_string = _normalize_string(params.get("value"))
    if as_string:
        return as_string
    ref = _coerce_secret_ref(params.get("value"))
    if not ref:
        return None
    mode = params.get("mode", "strict")
    if mode == "inspect":
        if params.get("allowEnvSecretRefRead") and ref.get("source") == "env":
            env_value = _normalize_string(os.environ.get(ref.get("id", "")))
            if env_value:
                return env_value
        return None
    raise FeishuSecretRefUnavailableError(params.get("path", ""), ref)


def _resolve_feishu_base_credentials(cfg: Optional[dict], mode: str) -> Optional[dict]:
    if not isinstance(cfg, dict):
        return None
    app_id = _resolve_feishu_secret_like({
        "value": cfg.get("appId"),
        "path": "channels.feishu.appId",
        "mode": mode,
        "allowEnvSecretRefRead": True,
    })
    app_secret = _resolve_feishu_secret_like({
        "value": cfg.get("appSecret"),
        "path": "channels.feishu.appSecret",
        "mode": mode,
        "allowEnvSecretRefRead": True,
    })
    if not app_id or not app_secret:
        return None
    return {
        "appId": app_id,
        "appSecret": app_secret,
        "domain": cfg.get("domain") or "feishu",
    }


def _resolve_feishu_event_secrets(cfg: Optional[dict], mode: str) -> dict:
    if not isinstance(cfg, dict):
        return {}
    connection_mode = cfg.get("connectionMode") or "websocket"
    if connection_mode == "webhook":
        encrypt_key = _resolve_feishu_secret_like({
            "value": cfg.get("encryptKey"),
            "path": "channels.feishu.encryptKey",
            "mode": mode,
            "allowEnvSecretRefRead": True,
        })
    else:
        encrypt_key = _normalize_string(cfg.get("encryptKey"))
    verification_token = _resolve_feishu_secret_like({
        "value": cfg.get("verificationToken"),
        "path": "channels.feishu.verificationToken",
        "mode": mode,
        "allowEnvSecretRefRead": True,
    })
    return {"encryptKey": encrypt_key, "verificationToken": verification_token}


def _list_feishu_account_ids(cfg: Any) -> list:
    if not isinstance(cfg, dict):
        return []
    feishu_cfg = (cfg.get("channels") or {}).get("feishu") if isinstance(cfg.get("channels"), dict) else None
    if not isinstance(feishu_cfg, dict):
        return []
    ids = []
    if _has_configured_account_value(feishu_cfg.get("appId")) and _has_configured_account_value(feishu_cfg.get("appSecret")):
        ids.append(DEFAULT_ACCOUNT_ID)
    accounts = feishu_cfg.get("accounts")
    if isinstance(accounts, dict):
        for key in accounts.keys():
            if key not in ids:
                ids.append(key)
    return ids


def resolve_default_feishu_account_selection(cfg: Any) -> dict:
    feishu_cfg = (cfg.get("channels") or {}).get("feishu") if isinstance(cfg, dict) and isinstance(cfg.get("channels"), dict) else None
    preferred = _normalize_optional_account_id(feishu_cfg.get("defaultAccount") if isinstance(feishu_cfg, dict) else None)
    if preferred:
        return {"accountId": preferred, "source": "explicit-default"}
    ids = _list_feishu_account_ids(cfg)
    if DEFAULT_ACCOUNT_ID in ids:
        return {"accountId": DEFAULT_ACCOUNT_ID, "source": "mapped-default"}
    return {"accountId": ids[0] if ids else DEFAULT_ACCOUNT_ID, "source": "fallback"}


def resolve_default_feishu_account_id(cfg: Any) -> str:
    return resolve_default_feishu_account_selection(cfg)["accountId"]


def _resolve_raw_feishu_account_config(accounts: Optional[dict], account_id: str) -> Optional[dict]:
    if not isinstance(accounts, dict):
        return None
    if account_id in accounts:
        return accounts[account_id]
    normalized = account_id.lower()
    for key in accounts.keys():
        if key.lower() == normalized:
            return accounts[key]
    return None


def _merge_feishu_account_config(cfg: Any, account_id: str) -> dict:
    if not isinstance(cfg, dict):
        return {}
    feishu_cfg = (cfg.get("channels") or {}).get("feishu") if isinstance(cfg.get("channels"), dict) else {}
    if not isinstance(feishu_cfg, dict):
        feishu_cfg = {}
    accounts = feishu_cfg.get("accounts")
    merged = dict(feishu_cfg)
    merged.pop("defaultAccount", None)
    account_cfg = _resolve_raw_feishu_account_config(accounts, account_id)
    if isinstance(account_cfg, dict):
        for key, value in account_cfg.items():
            merged[key] = value
    return merged


def resolve_feishu_credentials(cfg: Optional[dict], options: Optional[dict] = None) -> Optional[dict]:
    mode = "strict"
    if options:
        mode = options.get("mode") or ("inspect" if options.get("allowUnresolvedSecretRef") else "strict")
    base = _resolve_feishu_base_credentials(cfg, mode)
    if not base:
        return None
    event_secrets = _resolve_feishu_event_secrets(cfg, mode)
    return {**base, **event_secrets}


def inspect_feishu_credentials(cfg: Optional[dict]) -> Optional[dict]:
    return resolve_feishu_credentials(cfg, {"mode": "inspect"})


def _build_resolved_feishu_account(params: dict) -> ResolvedFeishuAccount:
    cfg = params.get("cfg", {})
    account_id_raw = params.get("accountId")
    has_explicit = isinstance(account_id_raw, str) and account_id_raw.strip() != ""
    default_selection = None if has_explicit else resolve_default_feishu_account_selection(cfg)
    account_id = _normalize_account_id(account_id_raw) if has_explicit else (default_selection or {}).get("accountId", DEFAULT_ACCOUNT_ID)
    selection_source = "explicit" if has_explicit else (default_selection or {}).get("source", "fallback")
    feishu_cfg = (cfg.get("channels") or {}).get("feishu") if isinstance(cfg, dict) and isinstance(cfg.get("channels"), dict) else None
    base_enabled = not (isinstance(feishu_cfg, dict) and feishu_cfg.get("enabled") is False)
    merged = _merge_feishu_account_config(cfg, account_id)
    account_enabled = merged.get("enabled") is not False
    enabled = base_enabled and account_enabled
    base_creds = _resolve_feishu_base_credentials(merged, params.get("baseMode", "inspect"))
    event_secrets = _resolve_feishu_event_secrets(merged, params.get("eventSecretMode", "inspect"))
    account_name = merged.get("name") if isinstance(merged, dict) else None
    name = account_name.strip() or None if isinstance(account_name, str) else None
    return {
        "accountId": account_id,
        "selectionSource": selection_source,
        "enabled": enabled,
        "configured": bool(base_creds),
        "name": name,
        "appId": base_creds.get("appId") if base_creds else None,
        "appSecret": base_creds.get("appSecret") if base_creds else None,
        "encryptKey": event_secrets.get("encryptKey"),
        "verificationToken": event_secrets.get("verificationToken"),
        "domain": (base_creds or {}).get("domain", "feishu"),
        "config": merged,
    }


def resolve_feishu_account(params: dict) -> ResolvedFeishuAccount:
    return _build_resolved_feishu_account({
        **params,
        "baseMode": "inspect",
        "eventSecretMode": "inspect",
    })


def resolve_feishu_runtime_account(params: dict, options: Optional[dict] = None) -> ResolvedFeishuAccount:
    event_mode = "strict" if options and options.get("requireEventSecrets") else "inspect"
    return _build_resolved_feishu_account({
        **params,
        "baseMode": "strict",
        "eventSecretMode": event_mode,
    })


def list_enabled_feishu_accounts(cfg: Any) -> list:
    accounts = []
    for account_id in _list_feishu_account_ids(cfg):
        account = resolve_feishu_account({"cfg": cfg, "accountId": account_id})
        if account.get("enabled") and account.get("configured"):
            accounts.append(account)
    return accounts


def list_feishu_account_ids(cfg: Any) -> list:
    return _list_feishu_account_ids(cfg)
