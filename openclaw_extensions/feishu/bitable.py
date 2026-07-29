import re
from typing import Any
from urllib.parse import urlparse, parse_qs

from .accounts import list_enabled_feishu_accounts
from .tool_result import (
    create_feishu_tool_client,
    json_tool_result,
    resolve_any_enabled_tools_config,
    tool_execution_error_result,
    unknown_tool_action_result,
)


def parse_bitable_url(url: str) -> dict:
    parsed = urlparse(url)
    path = parsed.path or ""
    app_token = None
    base_match = re.search(r"/base/([^/?#]+)", path)
    if base_match:
        app_token = base_match.group(1)
    else:
        wiki_match = re.search(r"/wiki/([^/?#]+)", path)
        if wiki_match:
            app_token = wiki_match.group(1)
    query = parse_qs(parsed.query or "")
    table_id = query.get("table", [None])[0]
    return {"appToken": app_token, "tableId": table_id}


async def get_meta(client: Any, url: str) -> dict:
    parsed = parse_bitable_url(url)
    app_token = parsed["appToken"]
    if not app_token:
        raise ValueError("Invalid bitable URL: cannot extract app_token")
    res = await client.bitable.app.get(app_token=app_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable get_meta failed"))
    data = res.get("data") or {}
    data["app_token"] = app_token
    if parsed["tableId"]:
        data["table_id"] = parsed["tableId"]
    return data


async def list_fields(client: Any, app_token: str, table_id: str, page_size: int = 100, page_token: str = "") -> dict:
    res = await client.bitable.app_table_field.list(app_token=app_token, table_id=table_id, page_size=page_size, page_token=page_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable list_fields failed"))
    return res.get("data") or {}


async def list_records(client: Any, app_token: str, table_id: str, page_size: int = 100, page_token: str = "", filter_condition: Any = None) -> dict:
    res = await client.bitable.app_table_record.list(
        app_token=app_token, table_id=table_id, page_size=page_size, page_token=page_token, filter=filter_condition,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable list_records failed"))
    return res.get("data") or {}


async def get_record(client: Any, app_token: str, table_id: str, record_id: str) -> dict:
    res = await client.bitable.app_table_record.get(app_token=app_token, table_id=table_id, record_id=record_id)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable get_record failed"))
    return res.get("data") or {}


async def create_record(client: Any, app_token: str, table_id: str, fields: dict) -> dict:
    res = await client.bitable.app_table_record.create(app_token=app_token, table_id=table_id, fields=fields)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable create_record failed"))
    return res.get("data") or {}


async def update_record(client: Any, app_token: str, table_id: str, record_id: str, fields: dict) -> dict:
    res = await client.bitable.app_table_record.update(app_token=app_token, table_id=table_id, record_id=record_id, fields=fields)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable update_record failed"))
    return res.get("data") or {}


async def create_app(client: Any, name: str, folder_token: str = "") -> dict:
    res = await client.bitable.app.create(name=name, folder_token=folder_token)
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable create_app failed"))
    return res.get("data") or {}


async def create_field(client: Any, app_token: str, table_id: str, field_name: str, field_type: int, property_: Any = None) -> dict:
    res = await client.bitable.app_table_field.create(
        app_token=app_token, table_id=table_id, field_name=field_name, type=field_type, property=property_,
    )
    if res.get("code") != 0:
        raise ValueError(res.get("msg", "Feishu bitable create_field failed"))
    return res.get("data") or {}


def register_feishu_bitable_tools(api: Any) -> None:
    if not getattr(api, "config", None):
        return
    accounts = list_enabled_feishu_accounts(api.config)
    if not accounts:
        return
    tools_cfg = resolve_any_enabled_tools_config(accounts)
    if not tools_cfg.get("bitable"):
        return

    def make_factory(name: str, label: str, description: str, parameters: dict, executor):
        def factory(ctx: dict) -> dict:
            async def execute(_tool_call_id: str, params: dict) -> dict:
                try:
                    client = create_feishu_tool_client({
                        "api": api,
                        "executeParams": params,
                        "defaultAccountId": ctx.get("agentAccountId"),
                    })
                    return await executor(client, params)
                except Exception as err:
                    return tool_execution_error_result(err)
            return {"name": name, "label": label, "description": description, "parameters": parameters, "execute": execute}
        return factory

    async def exec_get_meta(client: Any, params: dict) -> dict:
        return json_tool_result(await get_meta(client, params.get("url", "")))

    async def exec_list_fields(client: Any, params: dict) -> dict:
        return json_tool_result(await list_fields(client, params.get("app_token", ""), params.get("table_id", ""), params.get("page_size", 100), params.get("page_token", "")))

    async def exec_list_records(client: Any, params: dict) -> dict:
        return json_tool_result(await list_records(client, params.get("app_token", ""), params.get("table_id", ""), params.get("page_size", 100), params.get("page_token", ""), params.get("filter")))

    async def exec_get_record(client: Any, params: dict) -> dict:
        return json_tool_result(await get_record(client, params.get("app_token", ""), params.get("table_id", ""), params.get("record_id", "")))

    async def exec_create_record(client: Any, params: dict) -> dict:
        return json_tool_result(await create_record(client, params.get("app_token", ""), params.get("table_id", ""), params.get("fields", {})))

    async def exec_update_record(client: Any, params: dict) -> dict:
        return json_tool_result(await update_record(client, params.get("app_token", ""), params.get("table_id", ""), params.get("record_id", ""), params.get("fields", {})))

    async def exec_create_app(client: Any, params: dict) -> dict:
        return json_tool_result(await create_app(client, params.get("name", ""), params.get("folder_token", "")))

    async def exec_create_field(client: Any, params: dict) -> dict:
        return json_tool_result(await create_field(client, params.get("app_token", ""), params.get("table_id", ""), params.get("field_name", ""), int(params.get("field_type", 1)), params.get("property")))

    base_props = {
        "app_token": {"type": "string"},
        "table_id": {"type": "string"},
        "record_id": {"type": "string"},
        "fields": {"type": "object"},
        "page_size": {"type": "integer"},
        "page_token": {"type": "string"},
        "filter": {"type": "object"},
        "accountId": {"type": "string"},
    }

    tool_specs = [
        ("feishu_bitable_get_meta", "Feishu Bitable Get Meta", "Get Bitable app metadata from URL", {"type": "object", "properties": {"url": {"type": "string"}, "accountId": {"type": "string"}}, "required": ["url"]}, exec_get_meta),
        ("feishu_bitable_list_fields", "Feishu Bitable List Fields", "List fields in a Bitable table", {"type": "object", "properties": {**base_props}, "required": ["app_token", "table_id"]}, exec_list_fields),
        ("feishu_bitable_list_records", "Feishu Bitable List Records", "List records in a Bitable table", {"type": "object", "properties": {**base_props}, "required": ["app_token", "table_id"]}, exec_list_records),
        ("feishu_bitable_get_record", "Feishu Bitable Get Record", "Get a single Bitable record", {"type": "object", "properties": {**base_props}, "required": ["app_token", "table_id", "record_id"]}, exec_get_record),
        ("feishu_bitable_create_record", "Feishu Bitable Create Record", "Create a record in a Bitable table", {"type": "object", "properties": {**base_props}, "required": ["app_token", "table_id", "fields"]}, exec_create_record),
        ("feishu_bitable_update_record", "Feishu Bitable Update Record", "Update a record in a Bitable table", {"type": "object", "properties": {**base_props}, "required": ["app_token", "table_id", "record_id", "fields"]}, exec_update_record),
        ("feishu_bitable_create_app", "Feishu Bitable Create App", "Create a new Bitable application", {"type": "object", "properties": {"name": {"type": "string"}, "folder_token": {"type": "string"}, "accountId": {"type": "string"}}, "required": ["name"]}, exec_create_app),
        ("feishu_bitable_create_field", "Feishu Bitable Create Field", "Create a field in a Bitable table", {"type": "object", "properties": {**base_props, "field_name": {"type": "string"}, "field_type": {"type": "integer"}, "property": {"type": "object"}}, "required": ["app_token", "table_id", "field_name", "field_type"]}, exec_create_field),
    ]

    for name, label, description, parameters, executor in tool_specs:
        if hasattr(api, "registerTool"):
            api.registerTool(make_factory(name, label, description, parameters, executor), {"name": name})
