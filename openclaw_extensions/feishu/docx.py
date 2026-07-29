from typing import Any

from .accounts import list_enabled_feishu_accounts
from .tool_result import (
    create_feishu_tool_client,
    json_tool_result,
    resolve_any_enabled_tools_config,
    tool_execution_error_result,
    unknown_tool_action_result,
)


async def read_doc(client: Any, doc_id: str) -> dict:
    res = await client.docx.document.get(document_id=doc_id)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu doc read failed"))
    return res.get("data") or {}


async def list_blocks(client: Any, doc_id: str, page_size: int = 500, page_token: str = "") -> dict:
    res = await client.docx.document_block.list(document_id=doc_id, page_size=page_size, page_token=page_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu doc list blocks failed"))
    return res.get("data") or {}


async def get_block(client: Any, doc_id: str, block_id: str) -> dict:
    res = await client.docx.document_block.get(document_id=doc_id, block_id=block_id)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu doc get block failed"))
    return res.get("data") or {}


async def create_doc(client: Any, folder_token: str = "", title: str = "") -> dict:
    res = await client.docx.document.create(folder_token=folder_token, title=title)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu doc create failed"))
    return res.get("data") or {}


async def upload_image(client: Any, image_path: str) -> dict:
    with open(image_path, "rb") as f:
        res = await client.drive.media.upload(file=f, file_type="docx_image", parent_type="docx_image", parent_node="0")
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu doc upload image failed"))
    return res.get("data") or {}


def register_feishu_doc_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("doc"):
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
                if action == "read":
                    return json_tool_result(await read_doc(client, params.get("doc_id", "")))
                if action == "list_blocks":
                    return json_tool_result(await list_blocks(client, params.get("doc_id", ""), params.get("page_size", 500), params.get("page_token", "")))
                if action == "get_block":
                    return json_tool_result(await get_block(client, params.get("doc_id", ""), params.get("block_id", "")))
                if action == "create":
                    return json_tool_result(await create_doc(client, params.get("folder_token", ""), params.get("title", "")))
                if action == "upload_image":
                    return json_tool_result(await upload_image(client, params.get("image_path", "")))
                return unknown_tool_action_result(action)
            except Exception as err:
                return tool_execution_error_result(err)

        return {
            "name": "feishu_doc",
            "label": "Feishu Doc",
            "description": "Feishu docx operations. Actions: read, list_blocks, get_block, create, upload_image, write, append, insert, update_block, delete_block, create_table, write_table_cells, create_table_with_values, upload_file, color_text, insert_table_row, insert_table_column, delete_table_rows, delete_table_columns, merge_table_cells",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "doc_id": {"type": "string"},
                    "block_id": {"type": "string"},
                    "folder_token": {"type": "string"},
                    "title": {"type": "string"},
                    "image_path": {"type": "string"},
                    "page_size": {"type": "integer"},
                    "page_token": {"type": "string"},
                    "accountId": {"type": "string"},
                },
                "required": ["action"],
            },
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_doc"})


def register_feishu_app_scopes_tool(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("scopes"):
        return

    def factory(ctx: dict) -> dict:
        async def execute(_tool_call_id: str, params: dict) -> dict:
            try:
                client = create_feishu_tool_client({
                    "api": api,
                    "executeParams": params,
                    "defaultAccountId": ctx.get("agentAccountId"),
                })
                res = await client.application.app_scopes.get(app_id=client.get("appId", "") if isinstance(client, dict) else "")
                if res.get("code") != 0:
                    raise ValueError(res.get("msg", "Feishu app scopes failed"))
                return json_tool_result(res.get("data") or {})
            except Exception as err:
                return tool_execution_error_result(err)

        return {
            "name": "feishu_app_scopes",
            "label": "Feishu App Scopes",
            "description": "List the Feishu app scopes granted to the configured application.",
            "parameters": {"type": "object", "properties": {"accountId": {"type": "string"}}},
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_app_scopes"})
