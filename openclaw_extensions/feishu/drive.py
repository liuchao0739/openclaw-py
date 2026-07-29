from typing import Any

from .accounts import list_enabled_feishu_accounts
from .tool_result import (
    create_feishu_tool_client,
    json_tool_result,
    resolve_any_enabled_tools_config,
    tool_execution_error_result,
    unknown_tool_action_result,
)


async def list_files(client: Any, folder_token: str = "", page_size: int = 50, page_token: str = "") -> dict:
    res = await client.drive.file.list(folder_token=folder_token, page_size=page_size, page_token=page_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive list failed"))
    return res.get("data") or {}


async def get_file_info(client: Any, token: str) -> dict:
    res = await client.drive.file.get(token=token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive info failed"))
    return res.get("data") or {}


async def create_folder(client: Any, name: str, folder_token: str = "") -> dict:
    res = await client.drive.folder.create(name=name, folder_token=folder_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive create_folder failed"))
    return res.get("data") or {}


async def move_file(client: Any, file_token: str, type_: str, folder_token: str) -> dict:
    res = await client.drive.file.move(file_token=file_token, type=type_, folder_token=folder_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive move failed"))
    return res.get("data") or {}


async def delete_file(client: Any, file_token: str, type_: str) -> dict:
    res = await client.drive.file.delete(file_token=file_token, type=type_)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive delete failed"))
    return res.get("data") or {}


async def list_comments(client: Any, file_token: str, file_type: str = "docx") -> dict:
    res = await client.drive.file_comment.list(file_token=file_token, file_type=file_type)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive list_comments failed"))
    return res.get("data") or {}


async def list_comment_replies(client: Any, file_token: str, comment_id: str, file_type: str = "docx") -> dict:
    res = await client.drive.file_comment_reply.list(file_token=file_token, comment_id=comment_id, file_type=file_type)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive list_comment_replies failed"))
    return res.get("data") or {}


async def add_comment(client: Any, file_token: str, content: str, file_type: str = "docx", reply_to: str = "") -> dict:
    res = await client.drive.file_comment.create(
        file_token=file_token, file_type=file_type, content=content, reply_to=reply_to,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive add_comment failed"))
    return res.get("data") or {}


async def reply_comment(client: Any, file_token: str, comment_id: str, content: str, file_type: str = "docx") -> dict:
    res = await client.drive.file_comment_reply.create(
        file_token=file_token, comment_id=comment_id, file_type=file_type, content=content,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu drive reply_comment failed"))
    return res.get("data") or {}


async def deliver_comment_thread_text(client: Any, file_token: str, comment_id: str, file_type: str = "docx") -> str:
    comments = await list_comments(client, file_token, file_type)
    items = comments.get("items") or []
    target = next((c for c in items if c.get("comment_id") == comment_id), None)
    parts = []
    if target:
        body = target.get("content") or {}
        parts.append(_extract_comment_text(body))
    replies = await list_comment_replies(client, file_token, comment_id, file_type)
    reply_items = replies.get("items") or []
    for reply in reply_items:
        body = reply.get("content") or {}
        parts.append(_extract_comment_text(body))
    return "\n".join(p for p in parts if p)


def _extract_comment_text(body: Any) -> str:
    if isinstance(body, str):
        return body
    if isinstance(body, dict):
        elements = body.get("elements") or body.get("content") or []
        if isinstance(elements, list):
            texts = []
            for el in elements:
                if isinstance(el, dict):
                    text = el.get("text") or el.get("content") or ""
                    if text:
                        texts.append(text)
            return "".join(texts)
    return ""


def register_feishu_drive_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("drive"):
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
                    return json_tool_result(await list_files(client, params.get("folder_token", ""), params.get("page_size", 50), params.get("page_token", "")))
                if action == "info":
                    return json_tool_result(await get_file_info(client, params.get("token", "")))
                if action == "create_folder":
                    return json_tool_result(await create_folder(client, params.get("name", ""), params.get("folder_token", "")))
                if action == "move":
                    return json_tool_result(await move_file(client, params.get("file_token", ""), params.get("type", ""), params.get("folder_token", "")))
                if action == "delete":
                    return json_tool_result(await delete_file(client, params.get("file_token", ""), params.get("type", "")))
                if action == "list_comments":
                    return json_tool_result(await list_comments(client, params.get("token", ""), params.get("file_type", "docx")))
                if action == "list_comment_replies":
                    return json_tool_result(await list_comment_replies(client, params.get("token", ""), params.get("comment_id", ""), params.get("file_type", "docx")))
                if action == "add_comment":
                    return json_tool_result(await add_comment(client, params.get("token", ""), params.get("content", ""), params.get("file_type", "docx"), params.get("reply_to", "")))
                if action == "reply_comment":
                    return json_tool_result(await reply_comment(client, params.get("token", ""), params.get("comment_id", ""), params.get("content", ""), params.get("file_type", "docx")))
                return unknown_tool_action_result(action)
            except Exception as err:
                return tool_execution_error_result(err)

        return {
            "name": "feishu_drive",
            "label": "Feishu Drive",
            "description": "Feishu drive operations. Actions: list, info, create_folder, move, delete, list_comments, list_comment_replies, add_comment, reply_comment",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "token": {"type": "string"},
                    "file_token": {"type": "string"},
                    "comment_id": {"type": "string"},
                    "folder_token": {"type": "string"},
                    "name": {"type": "string"},
                    "type": {"type": "string"},
                    "file_type": {"type": "string"},
                    "content": {"type": "string"},
                    "reply_to": {"type": "string"},
                    "page_size": {"type": "integer"},
                    "page_token": {"type": "string"},
                    "accountId": {"type": "string"},
                },
                "required": ["action"],
            },
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_drive"})
