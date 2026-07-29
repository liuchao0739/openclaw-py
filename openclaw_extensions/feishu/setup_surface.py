from typing import Any

from .accounts import resolve_feishu_account, resolve_feishu_credentials
from .setup_core import feishu_setup_adapter


def run_feishu_login(cfg: Any, account_id: str = "default") -> Any:
    account = resolve_feishu_account({"cfg": cfg, "accountId": account_id})
    creds = resolve_feishu_credentials(account.get("config"), {"mode": "inspect"})
    if not creds:
        raise ValueError(f"Feishu credentials not configured for account {account_id}")
    return feishu_setup_adapter["applyAccountConfig"]({"cfg": cfg, "accountId": account_id})


async def feishu_setup_wizard(options: dict) -> Any:
    cfg = options.get("cfg", {})
    prompter = options.get("prompter")
    account_id = options.get("accountId", "default")
    if prompter and hasattr(prompter, "prompt"):
        app_id = await prompter.prompt("Enter Feishu App ID: ")
        app_secret = await prompter.prompt("Enter Feishu App Secret: ")
        if not isinstance(cfg, dict):
            cfg = {}
        channels = cfg.setdefault("channels", {})
        feishu_cfg = channels.setdefault("feishu", {})
        feishu_cfg["appId"] = app_id
        feishu_cfg["appSecret"] = app_secret
        feishu_cfg["enabled"] = True
    return run_feishu_login(cfg, account_id)


def create_clack_prompter() -> Any:
    class _Prompter:
        async def prompt(self, message: str) -> str:
            return input(message)

    return _Prompter()
