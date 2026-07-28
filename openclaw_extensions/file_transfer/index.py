from __future__ import annotations

import json

from openclaw.plugin_sdk.plugin_entry import OpenClawPluginApi, define_plugin_entry
from openclaw_extensions.file_transfer.shared.lazy_node_invoke_policy import (
    create_lazy_file_transfer_node_invoke_policy,
)
from openclaw_extensions.file_transfer.src.tools.descriptors import (
    DIR_FETCH_TOOL_DESCRIPTOR,
    DIR_LIST_TOOL_DESCRIPTOR,
    FILE_FETCH_TOOL_DESCRIPTOR,
    FILE_WRITE_TOOL_DESCRIPTOR,
)


def _read_node_command_params(params_json: str | None) -> dict:
    if params_json:
        return json.loads(params_json)
    return {}


async def _handle_file_fetch(params_json: str | None) -> str:
    from openclaw_extensions.file_transfer.src.node_host.file_fetch import handle_file_fetch
    params = _read_node_command_params(params_json)
    result = await handle_file_fetch(params)
    return json.dumps(result)


async def _handle_dir_list(params_json: str | None) -> str:
    from openclaw_extensions.file_transfer.src.node_host.dir_list import handle_dir_list
    params = _read_node_command_params(params_json)
    result = await handle_dir_list(params)
    return json.dumps(result)


async def _handle_dir_fetch(params_json: str | None) -> str:
    from openclaw_extensions.file_transfer.src.node_host.dir_fetch import handle_dir_fetch
    params = _read_node_command_params(params_json)
    result = await handle_dir_fetch(params)
    return json.dumps(result)


async def _handle_file_write(params_json: str | None) -> str:
    from openclaw_extensions.file_transfer.src.node_host.file_write import handle_file_write
    params = _read_node_command_params(params_json)
    result = await handle_file_write(params)
    return json.dumps(result)


file_transfer_node_host_commands = [
    {
        "command": "file.fetch",
        "cap": "file",
        "dangerous": True,
        "handle": _handle_file_fetch,
    },
    {
        "command": "dir.list",
        "cap": "file",
        "dangerous": True,
        "handle": _handle_dir_list,
    },
    {
        "command": "dir.fetch",
        "cap": "file",
        "dangerous": True,
        "handle": _handle_dir_fetch,
    },
    {
        "command": "file.write",
        "cap": "file",
        "dangerous": True,
        "handle": _handle_file_write,
    },
]


def _register(api: OpenClawPluginApi) -> None:
    api.register_node_invoke_policy(create_lazy_file_transfer_node_invoke_policy())

    async def _load_file_fetch_tool():
        from openclaw_extensions.file_transfer.src.tools.file_fetch_tool import create_file_fetch_tool
        return await create_file_fetch_tool()

    async def _load_dir_list_tool():
        from openclaw_extensions.file_transfer.src.tools.dir_list_tool import create_dir_list_tool
        return await create_dir_list_tool()

    async def _load_dir_fetch_tool():
        from openclaw_extensions.file_transfer.src.tools.dir_fetch_tool import create_dir_fetch_tool
        return await create_dir_fetch_tool()

    async def _load_file_write_tool():
        from openclaw_extensions.file_transfer.src.tools.file_write_tool import create_file_write_tool
        return await create_file_write_tool()

    api.register_tool(
        _create_lazy_tool(FILE_FETCH_TOOL_DESCRIPTOR, _load_file_fetch_tool)
    )
    api.register_tool(
        _create_lazy_tool(DIR_LIST_TOOL_DESCRIPTOR, _load_dir_list_tool)
    )
    api.register_tool(
        _create_lazy_tool(DIR_FETCH_TOOL_DESCRIPTOR, _load_dir_fetch_tool)
    )
    api.register_tool(
        _create_lazy_tool(FILE_WRITE_TOOL_DESCRIPTOR, _load_file_write_tool)
    )


def _create_lazy_tool(descriptor: dict, load_tool: Any) -> dict:
    tool_future = {"promise": None}

    async def _load_once():
        if tool_future["promise"] is None:
            tool_future["promise"] = load_tool()
        return await tool_future["promise"]

    async def _execute(tool_call_id: str, args: dict, signal=None, on_update=None):
        tool = await _load_once()
        return await tool["execute"](tool_call_id, args)

    result = dict(descriptor)
    result["execute"] = _execute
    return result


default = define_plugin_entry(
    id="file-transfer",
    name="File Transfer",
    description="Fetch, list, and write files on paired nodes via dedicated node commands.",
    nodeHostCommands=file_transfer_node_host_commands,
    register=_register,
)