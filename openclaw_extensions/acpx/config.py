import os
import re
from typing import Any, Optional

from .config_schema import (
    ACPX_OPENCLAW_TOOLS_MCP_SERVER_NAME,
    ACPX_PLUGIN_TOOLS_MCP_SERVER_NAME,
    DEFAULT_NON_INTERACTIVE_POLICY,
    DEFAULT_PERMISSION_MODE,
    DEFAULT_QUEUE_OWNER_TTL_SECONDS,
    DEFAULT_STRICT_WINDOWS_CMD_WRAPPER,
    DEFAULT_ACPX_TIMEOUT_SECONDS,
    AcpxMcpServer,
    McpServerConfig,
    ResolvedAcpxPluginConfig,
    parse_acpx_plugin_config,
)


def _normalize_lowercase_string_or_empty(value: Any) -> str:
    if isinstance(value, str):
        return value.lower()
    return ""


def _shell_quote_command_arg(arg: str) -> str:
    if not re.search(r"[\s'\"\\$|&;<>{}()*?[\]~`]", arg):
        return arg
    return "'" + arg.replace("'", "'\"'\"'") + "'"


def _is_acpx_plugin_root(dir_path: str) -> bool:
    return (
        os.path.exists(os.path.join(dir_path, "openclaw.plugin.json"))
        and os.path.exists(os.path.join(dir_path, "package.json"))
    )


def resolve_acpx_plugin_root(module_file: Optional[str] = None) -> str:
    base_dir = os.path.dirname(os.path.abspath(module_file or __file__))
    cursor = base_dir
    for _ in range(3):
        if _is_acpx_plugin_root(cursor):
            return cursor
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent
    for _ in range(5):
        candidates = [
            os.path.join(cursor, "extensions", "acpx"),
            os.path.join(cursor, "dist", "extensions", "acpx"),
            os.path.join(cursor, "dist-runtime", "extensions", "acpx"),
        ]
        for candidate in candidates:
            if _is_acpx_plugin_root(candidate):
                return candidate
        parent = os.path.dirname(cursor)
        if parent == cursor:
            break
        cursor = parent
    return os.path.dirname(base_dir)


def _resolve_openclaw_root(current_root: str) -> str:
    if os.path.basename(current_root) == "acpx" and os.path.basename(os.path.dirname(current_root)) == "extensions":
        parent = os.path.dirname(os.path.dirname(current_root))
        if os.path.basename(parent) == "dist":
            return os.path.dirname(parent)
        return parent
    return os.path.abspath(os.path.join(current_root, ".."))


def _resolve_plugin_tools_mcp_server_config(module_file: Optional[str] = None) -> McpServerConfig:
    plugin_root = resolve_acpx_plugin_root(module_file)
    openclaw_root = _resolve_openclaw_root(plugin_root)
    dist_entry = os.path.join(openclaw_root, "dist", "mcp", "plugin-tools-serve.js")
    if os.path.exists(dist_entry):
        return {"command": _python_executable(), "args": [dist_entry]}
    source_entry = os.path.join(openclaw_root, "src", "mcp", "plugin-tools-serve.ts")
    return {"command": _python_executable(), "args": [source_entry]}


def _resolve_openclaw_tools_mcp_server_config(module_file: Optional[str] = None) -> McpServerConfig:
    plugin_root = resolve_acpx_plugin_root(module_file)
    openclaw_root = _resolve_openclaw_root(plugin_root)
    dist_entry = os.path.join(openclaw_root, "dist", "mcp", "openclaw-tools-serve.js")
    if os.path.exists(dist_entry):
        return {"command": _python_executable(), "args": [dist_entry]}
    source_entry = os.path.join(openclaw_root, "src", "mcp", "openclaw-tools-serve.ts")
    return {"command": _python_executable(), "args": [source_entry]}


def _python_executable() -> str:
    return os.environ.get("OPENCLAW_PYTHON", "python3")


def _resolve_configured_mcp_servers(
    mcp_servers: Optional[dict],
    plugin_tools_mcp_bridge: bool,
    openclaw_tools_mcp_bridge: bool,
    module_file: Optional[str] = None,
) -> dict:
    resolved = dict(mcp_servers or {})
    if plugin_tools_mcp_bridge and ACPX_PLUGIN_TOOLS_MCP_SERVER_NAME in resolved:
        raise ValueError(
            f"mcpServers.{ACPX_PLUGIN_TOOLS_MCP_SERVER_NAME} is reserved when pluginToolsMcpBridge=true"
        )
    if openclaw_tools_mcp_bridge and ACPX_OPENCLAW_TOOLS_MCP_SERVER_NAME in resolved:
        raise ValueError(
            f"mcpServers.{ACPX_OPENCLAW_TOOLS_MCP_SERVER_NAME} is reserved when openClawToolsMcpBridge=true"
        )
    if plugin_tools_mcp_bridge:
        resolved[ACPX_PLUGIN_TOOLS_MCP_SERVER_NAME] = _resolve_plugin_tools_mcp_server_config(module_file)
    if openclaw_tools_mcp_bridge:
        resolved[ACPX_OPENCLAW_TOOLS_MCP_SERVER_NAME] = _resolve_openclaw_tools_mcp_server_config(module_file)
    return resolved


def to_acp_mcp_servers(mcp_servers: dict) -> list:
    result: list = []
    for name, server in (mcp_servers or {}).items():
        if not isinstance(server, dict):
            continue
        env_list = []
        env = server.get("env") or {}
        if isinstance(env, dict):
            for env_name, env_value in env.items():
                env_list.append({"name": env_name, "value": str(env_value)})
        entry: AcpxMcpServer = {
            "name": name,
            "command": server.get("command", ""),
            "args": list(server.get("args") or []),
            "env": env_list,
        }
        result.append(entry)
    return result


def resolve_acpx_plugin_config(params: dict) -> ResolvedAcpxPluginConfig:
    raw_config = params.get("rawConfig")
    parsed = parse_acpx_plugin_config(raw_config)
    normalized = parsed or {}
    workspace_dir = (params.get("workspaceDir") or "").strip() or os.getcwd()
    fallback_cwd = workspace_dir
    cwd = os.path.abspath((normalized.get("cwd") or "").strip() or fallback_cwd)
    state_dir = os.path.abspath((normalized.get("stateDir") or "").strip() or os.path.join(workspace_dir, "state"))
    plugin_tools_mcp_bridge = normalized.get("pluginToolsMcpBridge") is True
    openclaw_tools_mcp_bridge = normalized.get("openClawToolsMcpBridge") is True
    mcp_servers = _resolve_configured_mcp_servers(
        normalized.get("mcpServers"),
        plugin_tools_mcp_bridge,
        openclaw_tools_mcp_bridge,
        params.get("moduleFile"),
    )
    agents: dict = {}
    raw_agents = normalized.get("agents") or {}
    if isinstance(raw_agents, dict):
        for name, entry in raw_agents.items():
            if not isinstance(entry, dict):
                continue
            cmd = (entry.get("command") or "").strip()
            cmd_args = entry.get("args") or []
            if cmd_args:
                full_command = f"{cmd} {' '.join(_shell_quote_command_arg(a) for a in cmd_args)}"
            else:
                full_command = cmd
            agents[_normalize_lowercase_string_or_empty(name)] = full_command
    probe_agent = _normalize_lowercase_string_or_empty(normalized.get("probeAgent")) or None
    timeout_seconds = normalized.get("timeoutSeconds")
    if timeout_seconds is None:
        timeout_seconds = DEFAULT_ACPX_TIMEOUT_SECONDS
    queue_owner_ttl = normalized.get("queueOwnerTtlSeconds")
    if queue_owner_ttl is None:
        queue_owner_ttl = DEFAULT_QUEUE_OWNER_TTL_SECONDS
    strict_windows_cmd_wrapper = normalized.get("strictWindowsCmdWrapper")
    if strict_windows_cmd_wrapper is None:
        strict_windows_cmd_wrapper = DEFAULT_STRICT_WINDOWS_CMD_WRAPPER
    return {
        "cwd": cwd,
        "stateDir": state_dir,
        "probeAgent": probe_agent,
        "permissionMode": normalized.get("permissionMode") or DEFAULT_PERMISSION_MODE,
        "nonInteractivePermissions": normalized.get("nonInteractivePermissions") or DEFAULT_NON_INTERACTIVE_POLICY,
        "pluginToolsMcpBridge": plugin_tools_mcp_bridge,
        "openClawToolsMcpBridge": openclaw_tools_mcp_bridge,
        "strictWindowsCmdWrapper": strict_windows_cmd_wrapper,
        "timeoutSeconds": timeout_seconds,
        "queueOwnerTtlSeconds": queue_owner_ttl,
        "legacyCompatibilityConfig": {
            "strictWindowsCmdWrapper": strict_windows_cmd_wrapper,
            "queueOwnerTtlSeconds": queue_owner_ttl,
        },
        "mcpServers": mcp_servers,
        "agents": agents,
    }
