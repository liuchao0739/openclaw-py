import os

BINDING_DATA_VERSION = 1


def create_codex_conversation_binding_data(params: dict) -> dict:
    agent_dir = (params.get("agentDir") or "").strip()
    agent_id = (params.get("agentId") or "").strip()
    data = {
        "kind": "codex-app-server-session",
        "version": BINDING_DATA_VERSION,
        "sessionFile": params["sessionFile"],
        "workspaceDir": params["workspaceDir"],
    }
    if agent_dir:
        data["agentDir"] = agent_dir
    if agent_id:
        data["agentId"] = agent_id
    return data


def create_codex_cli_node_conversation_binding_data(params: dict) -> dict:
    cwd = (params.get("cwd") or "").strip()
    data = {
        "kind": "codex-cli-node-session",
        "version": BINDING_DATA_VERSION,
        "nodeId": params["nodeId"],
        "sessionId": params["sessionId"],
    }
    if cwd:
        data["cwd"] = cwd
    return data


def read_codex_conversation_binding_data(binding):
    if not binding:
        return None
    data = binding.get("data") if isinstance(binding, dict) else None
    if not data or not isinstance(data, dict) or isinstance(data, list):
        return None
    return read_codex_conversation_binding_data_record(data)


def read_codex_conversation_binding_data_record(data: dict):
    if data.get("kind") == "codex-cli-node-session":
        if (
            data.get("version") != BINDING_DATA_VERSION
            or not isinstance(data.get("nodeId"), str)
            or not data["nodeId"].strip()
            or not isinstance(data.get("sessionId"), str)
            or not data["sessionId"].strip()
        ):
            return None
        cwd_value = data.get("cwd")
        return {
            "kind": "codex-cli-node-session",
            "version": BINDING_DATA_VERSION,
            "nodeId": data["nodeId"].strip(),
            "sessionId": data["sessionId"].strip(),
            "cwd": cwd_value.strip() if isinstance(cwd_value, str) and cwd_value.strip() else None,
        }
    if data.get("kind") != "codex-app-server-session":
        return None
    if data.get("version") != BINDING_DATA_VERSION or not isinstance(data.get("sessionFile"), str) or not data["sessionFile"].strip():
        return None
    workspace_dir_value = data.get("workspaceDir")
    agent_dir_value = data.get("agentDir")
    agent_id_value = data.get("agentId")
    return {
        "kind": "codex-app-server-session",
        "version": BINDING_DATA_VERSION,
        "sessionFile": data["sessionFile"],
        "workspaceDir": workspace_dir_value if isinstance(workspace_dir_value, str) and workspace_dir_value.strip() else os.getcwd(),
        "agentDir": agent_dir_value if isinstance(agent_dir_value, str) and agent_dir_value.strip() else None,
        "agentId": agent_id_value if isinstance(agent_id_value, str) and agent_id_value.strip() else None,
    }


def resolve_codex_default_workspace_dir(plugin_config) -> str:
    app_server = plugin_config.get("appServer") if isinstance(plugin_config, dict) else None
    app_server = app_server if isinstance(app_server, dict) else {}
    configured = _read_string(app_server, "defaultWorkspaceDir")
    return configured or os.getcwd()


def _read_string(record, key: str):
    value = record.get(key) if isinstance(record, dict) else None
    return value.strip() if isinstance(value, str) and value.strip() else None
