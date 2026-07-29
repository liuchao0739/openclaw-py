from typing import Any

from .accounts import list_enabled_feishu_accounts
from .tool_result import (
    create_feishu_tool_client,
    json_tool_result,
    resolve_any_enabled_tools_config,
    tool_execution_error_result,
    unknown_tool_action_result,
)


async def list_spaces(client: Any, page_size: int = 50, page_token: str = "") -> dict:
    res = await client.wiki.space.list(page_size=page_size, page_token=page_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki spaces failed"))
    return res.get("data") or {}


async def list_nodes(client: Any, space_id: str, parent_node_token: str = "", page_size: int = 50, page_token: str = "") -> dict:
    res = await client.wiki.space_node.list(
        space_id=space_id, parent_node_token=parent_node_token, page_size=page_size, page_token=page_token,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki nodes failed"))
    return res.get("data") or {}


async def get_node(client: Any, token: str, obj_type: str = "wiki") -> dict:
    res = await client.wiki.space_node.get(token=token, obj_type=obj_type)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki get failed"))
    return res.get("data") or {}


async def search_wiki(client: Any, query: str, page_size: int = 20, page_token: str = "") -> dict:
    res = await client.wiki.task.search(query=query, page_size=page_size, page_token=page_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki search failed"))
    return res.get("data") or {}


async def create_node(client: Any, space_id: str, parent_node_token: str, node_type: str, title: str) -> dict:
    res = await client.wiki.space_node.create(
        space_id=space_id, parent_node_token=parent_node_token, node_type=node_type, title=title,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki create failed"))
    return res.get("data") or {}


async def move_node(client: Any, space_id: str, node_token: str, target_space_id: str = "", target_parent_token: str = "") -> dict:
    res = await client.wiki.space_node.move(
        space_id=space_id, node_token=node_token, target_space_id=target_space_id, target_parent_token=target_parent_token,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki move failed"))
    return res.get("data") or {}


async def rename_node(client: Any, space_id: str, node_token: str, new_title: str) -> dict:
    res = await client.wiki.space_node.update(space_id=space_id, node_token=node_token, title=new_title)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu wiki rename failed"))
    return res.get("data") or {}


def register_feishu_wiki_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("wiki"):
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
                if action == "spaces":
                    return json_tool_result(await list_spaces(client, params.get("page_size", 50), params.get("page_token", "")))
                if action == "nodes":
                    return json_tool_result(await list_nodes(client, params.get("space_id", ""), params.get("parent_node_token", ""), params.get("page_size", 50), params.get("page_token", "")))
                if action == "get":
                    return json_tool_result(await get_node(client, params.get("token", ""), params.get("obj_type", "wiki")))
                if action == "search":
                    return json_tool_result(await search_wiki(client, params.get("query", ""), params.get("page_size", 20), params.get("page_token", "")))
                if action == "create":
                    return json_tool_result(await create_node(client, params.get("space_id", ""), params.get("parent_node_token", ""), params.get("node_type", "docx"), params.get("title", "")))
                if action == "move":
                    return json_tool_result(await move_node(client, params.get("space_id", ""), params.get("node_token", ""), params.get("target_space_id", ""), params.get("target_parent_token", "")))
                if action == "rename":
                    return json_tool_result(await rename_node(client, params.get("space_id", ""), params.get("node_token", ""), params.get("title", "")))
                return unknown_tool_action_result(action)
            except Exception as err:
                return tool_execution_error_result(err)

        return {
            "name": "feishu_wiki",
            "label": "Feishu Wiki",
            "description": "Feishu wiki operations. Actions: spaces, nodes, get, search, create, move, rename",
            "parameters": {
                "type": "object",
                "properties": {
                    "action": {"type": "string"},
                    "space_id": {"type": "string"},
                    "parent_node_token": {"type": "string"},
                    "node_token": {"type": "string"},
                    "token": {"type": "string"},
                    "obj_type": {"type": "string"},
                    "query": {"type": "string"},
                    "node_type": {"type": "string"},
                    "title": {"type": "string"},
                    "target_space_id": {"type": "string"},
                    "target_parent_token": {"type": "string"},
                    "page_size": {"type": "integer"},
                    "page_token": {"type": "string"},
                    "accountId": {"type": "string"},
                },
                "required": ["action"],
            },
            "execute": execute,
        }

    if hasattr(api, "registerTool"):
        api.registerTool(factory, {"name": "feishu_wiki"})
