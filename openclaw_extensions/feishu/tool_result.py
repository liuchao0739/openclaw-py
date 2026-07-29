import json
from typing import Any


def json_tool_result(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "details": data}


def tool_execution_error_result(err: Any) -> dict:
    message = str(err) if not isinstance(err, Exception) else (err.args[0] if err.args else str(err))
    return {"content": [{"type": "text", "text": f"Error: {message}"}], "isError": True}


def unknown_tool_action_result(action: Any) -> dict:
    return {"content": [{"type": "text", "text": f"Unknown action: {action}"}], "isError": True}


def resolve_any_enabled_tools_config(accounts: list) -> dict:
    for account in accounts:
        config = account.get("config") or {}
        tools = config.get("tools")
        if isinstance(tools, dict):
            merged = {
                "doc": tools.get("doc", True),
                "chat": tools.get("chat", True),
                "wiki": tools.get("wiki", True),
                "drive": tools.get("drive", True),
                "perm": tools.get("perm", True),
                "scopes": tools.get("scopes", True),
                "bitable": tools.get("bitable", tools.get("base", True)),
            }
            if any(merged.values()):
                return merged
    return {
        "doc": True,
        "chat": True,
        "wiki": True,
        "drive": True,
        "perm": True,
        "scopes": True,
        "bitable": True,
    }


def create_feishu_tool_client(params: dict) -> Any:
    from .client import create_feishu_client
    api = params.get("api")
    execute_params = params.get("executeParams") or {}
    default_account_id = params.get("defaultAccountId")
    account_id = execute_params.get("accountId") or default_account_id
    accounts = []
    if api and getattr(api, "config", None):
        from .accounts import list_enabled_feishu_accounts
        accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        raise ValueError("No enabled Feishu accounts configured")
    account = next((a for a in accounts if a.get("accountId") == account_id), accounts[0])
    return create_feishu_client(account)
