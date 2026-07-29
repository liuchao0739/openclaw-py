from typing import Any

from .accounts import list_enabled_feishu_accounts
from .tool_result import (
    create_feishu_tool_client,
    json_tool_result,
    resolve_any_enabled_tools_config,
    tool_execution_error_result,
    unknown_tool_action_result,
)


async def list_members(client: Any, token: str, type_: str) -> dict:
    res = await client.drive.permission_member.list(token=token, type=type_)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu perm list failed"))
    data = res.get("data") or {}
    items = data.get("items") or []
    return {
        "members": [
            {
                "member_type": m.get("member_type"),
                "member_id": m.get("member_id"),
                "perm": m.get("perm"),
                "name": m.get("name"),
            }
            for m in items
        ]
    }


async def add_member(client: Any, token: str, type_: str, member_type: str, member_id: str, perm: str) -> dict:
    res = await client.drive.permission_member.create(
        token=token, type=type_, need_notification=False,
        member_type=member_type, member_id=member_id, perm=perm,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu perm add failed"))
    return {"success": True, "member": (res.get("data") or {}).get("member")}


async def remove_member(client: Any, token: str, type_: str, member_type: str, member_id: str) -> dict:
    res = await client.drive.permission_member.delete(
        token=token, member_id=member_id, type=type_, member_type=member_type,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu perm remove failed"))
    return {"success": True}


def register_feishu_perm_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("perm"):
        return

    def factory(ctx: dict) -> dict:
        default_account_id = ctx.get("agentAccountId")

        async def execute(_tool_call_id: str, params: dict) -> dict:
            try:
                client = create_feishu_tool_client({
                    "api": api,
                    "executeParams": params,
                    "defaultAccountId": default_account_id,
                })
                action = params.get("action")
                if action == "list":
                    return json_tool_result(await list_members(client, params.get("token", ""), params.get("type", "")))
                if action == "add":
                    return json_tool_result(await add_member(
                        client, params.get("token", ""), params.get("type", ""),
                        params.get("member_type", ""), params.get("member_id", ""), params.get("perm", ""),
                    ))
                if action == "remove":
                    return json_tool_result(await remove_member(
                        client, params.get("token", ""), params.get("type", ""),
                        params.get("member_type", ""), params.get("member_id", ""),
                    ))
                return unknown_tool_action_result(action)
            except Exception as err:
                return tool_execution_error_result(err)

        return {
            "name": "feishu_perm",
            "label": "Feishu Perm",
            "description": "Feishu permission management. Actions: list, add, remove",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["list", "add", "remove"]},
                    "token": {"type": "string"},
                    "type": {"type": "string"},
                    "member_type": {"type": "string"},
                    "member_id": {"type": "string"},
                    "perm": {"type": "string", "enum": ["view", "edit", "full_access"]},
                    "accountId": {"type": "string"},
                },
                "required": ["action", "token", "type"],
            },
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_perm"})
