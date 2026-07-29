import json
from typing import Any, Optional

from .accounts import list_enabled_feishu_accounts
from .client import create_feishu_client


def _json_result(data: Any) -> dict:
    return {"content": [{"type": "text", "text": json.dumps(data, indent=2)}], "details": data}


def _read_chat_page_size(params: dict) -> Optional[int]:
    value = params.get("page_size")
    if value is None:
        return None
    if isinstance(value, bool):
        raise ValueError("page_size must be a positive integer between 1 and 100")
    if isinstance(value, int) and value > 0:
        if value > 100:
            raise ValueError("page_size must be a positive integer between 1 and 100")
        return value
    if isinstance(value, float) and value.is_integer() and value > 0:
        if value > 100:
            raise ValueError("page_size must be a positive integer between 1 and 100")
        return int(value)
    raise ValueError("page_size must be a positive integer between 1 and 100")


async def get_chat_info(client: Any, chat_id: str) -> dict:
    res = await client.im.chat.get(chat_id=chat_id)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu chat get failed"))
    chat = res.get("data") or {}
    return {
        "chat_id": chat_id,
        "name": chat.get("name"),
        "description": chat.get("description"),
        "owner_id": chat.get("owner_id"),
        "tenant_key": chat.get("tenant_key"),
        "user_count": chat.get("user_count"),
        "chat_mode": chat.get("chat_mode"),
        "chat_type": chat.get("chat_type"),
        "join_message_visibility": chat.get("join_message_visibility"),
        "leave_message_visibility": chat.get("leave_message_visibility"),
        "membership_approval": chat.get("membership_approval"),
        "moderation_permission": chat.get("moderation_permission"),
        "avatar": chat.get("avatar"),
    }


async def get_chat_members(
    client: Any,
    chat_id: str,
    page_size: Optional[int] = None,
    page_token: Optional[str] = None,
    member_id_type: str = "open_id",
) -> dict:
    size = max(1, min(100, page_size)) if page_size else 50
    res = await client.im.chat_members.get(
        chat_id=chat_id,
        page_size=size,
        page_token=page_token,
        member_id_type=member_id_type,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu chat members get failed"))
    data = res.get("data") or {}
    items = data.get("items") or []
    return {
        "chat_id": chat_id,
        "has_more": data.get("has_more"),
        "page_token": data.get("page_token"),
        "members": [
            {
                "member_id": item.get("member_id"),
                "name": item.get("name"),
                "tenant_key": item.get("tenant_key"),
                "member_id_type": item.get("member_id_type"),
            }
            for item in items
        ],
    }


async def get_feishu_member_info(
    client: Any,
    member_id: str,
    member_id_type: str = "open_id",
) -> dict:
    res = await client.contact.user.get(
        user_id=member_id,
        user_id_type=member_id_type,
        department_id_type="open_department_id",
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu user get failed"))
    user = (res.get("data") or {}).get("user") or {}
    return {
        "member_id": member_id,
        "member_id_type": member_id_type,
        "open_id": user.get("open_id"),
        "user_id": user.get("user_id"),
        "union_id": user.get("union_id"),
        "name": user.get("name"),
        "en_name": user.get("en_name"),
        "nickname": user.get("nickname"),
        "email": user.get("email"),
        "enterprise_email": user.get("enterprise_email"),
        "mobile": user.get("mobile"),
        "mobile_visible": user.get("mobile_visible"),
        "status": user.get("status"),
        "avatar": user.get("avatar"),
        "department_ids": user.get("department_ids"),
        "department_path": user.get("department_path"),
        "leader_user_id": user.get("leader_user_id"),
        "city": user.get("city"),
        "country": user.get("country"),
        "work_station": user.get("work_station"),
        "join_time": user.get("join_time"),
        "is_tenant_manager": user.get("is_tenant_manager"),
        "employee_no": user.get("employee_no"),
        "employee_type": user.get("employee_type"),
        "description": user.get("description"),
        "job_title": user.get("job_title"),
        "geo": user.get("geo"),
    }


def register_feishu_chat_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return

    def factory(ctx: dict) -> dict:
        default_account_id = ctx.get("agentAccountId")

        async def execute(_tool_call_id: str, params: dict) -> dict:
            account_id = params.get("accountId") or default_account_id
            account = next((a for a in accounts if a.get("accountId") == account_id), accounts[0])
            client = create_feishu_client(account)
            action = params.get("action")
            try:
                if action == "info":
                    return _json_result(await get_chat_info(client, params.get("chat_id", "")))
                if action == "members":
                    return _json_result(await get_chat_members(
                        client,
                        params.get("chat_id", ""),
                        _read_chat_page_size(params),
                        params.get("page_token"),
                        params.get("member_id_type", "open_id"),
                    ))
                if action == "member_info":
                    return _json_result(await get_feishu_member_info(
                        client,
                        params.get("member_id", ""),
                        params.get("member_id_type", "open_id"),
                    ))
                return {"content": [{"type": "text", "text": f"Unknown action: {action}"}]}
            except Exception as err:
                return {"content": [{"type": "text", "text": f"Feishu chat error: {err}"}], "isError": True}

        return {
            "name": "feishu_chat",
            "label": "Feishu Chat",
            "description": "Feishu chat information. Actions: info, members, member_info",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string", "enum": ["info", "members", "member_info"]},
                    "chat_id": {"type": "string"},
                    "member_id": {"type": "string"},
                    "member_id_type": {"type": "string", "enum": ["open_id", "user_id", "union_id"]},
                    "page_size": {"type": "integer"},
                    "page_token": {"type": "string"},
                    "accountId": {"type": "string"},
                },
                "required": ["action"],
            },
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_chat"})
