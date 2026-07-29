from typing import List, Optional, TypedDict


class ModelCost(TypedDict, total=False):
    input: float
    output: float
    cacheRead: float
    cacheWrite: float


ACPX_PERMISSION_MODES = ("approve-all", "approve-reads", "deny-all")
ACPX_NON_INTERACTIVE_POLICIES = ("deny", "fail")

DEFAULT_ACPX_TIMEOUT_SECONDS = 120

DEFAULT_PERMISSION_MODE = "approve-reads"
DEFAULT_NON_INTERACTIVE_POLICY = "fail"
DEFAULT_QUEUE_OWNER_TTL_SECONDS = 0.1
DEFAULT_STRICT_WINDOWS_CMD_WRAPPER = True


class McpServerConfig(TypedDict, total=False):
    command: str
    args: List[str]
    env: dict


class AcpxMcpServer(TypedDict):
    name: str
    command: str
    args: List[str]
    env: List[dict]


class AcpxAgentEntry(TypedDict, total=False):
    command: str
    args: List[str]


class AcpxPluginConfig(TypedDict, total=False):
    cwd: str
    stateDir: str
    probeAgent: str
    permissionMode: str
    nonInteractivePermissions: str
    pluginToolsMcpBridge: bool
    openClawToolsMcpBridge: bool
    strictWindowsCmdWrapper: bool
    timeoutSeconds: float
    queueOwnerTtlSeconds: float
    mcpServers: dict
    agents: dict


class ResolvedAcpxPluginConfig(TypedDict):
    cwd: str
    stateDir: str
    permissionMode: str
    nonInteractivePermissions: str
    pluginToolsMcpBridge: bool
    openClawToolsMcpBridge: bool
    strictWindowsCmdWrapper: bool
    queueOwnerTtlSeconds: float
    mcpServers: dict
    agents: dict


_VALID_PERMISSION_MODES = set(ACPX_PERMISSION_MODES)
_VALID_NON_INTERACTIVE_POLICIES = set(ACPX_NON_INTERACTIVE_POLICIES)


def _non_empty_trimmed_string(value, message: str) -> Optional[str]:
    if value is None:
        return None
    if not isinstance(value, str):
        raise ValueError(message)
    trimmed = value.strip()
    if not trimmed:
        raise ValueError(message)
    return trimmed


def _validate_mcp_server_config(name: str, value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError(f"mcpServers.{name} must be an object")
    command = _non_empty_trimmed_string(
        value.get("command"),
        f"mcpServers.{name}.command must be a non-empty string",
    )
    if command is None:
        raise ValueError(f"mcpServers.{name}.command must be a non-empty string")
    args = value.get("args")
    if args is not None:
        if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
            raise ValueError(f"mcpServers.{name}.args must be an array of strings")
    env = value.get("env")
    if env is not None:
        if not isinstance(env, dict) or not all(
            isinstance(k, str) and isinstance(v, str) for k, v in env.items()
        ):
            raise ValueError(f"mcpServers.{name}.env must be an object of strings")
    result: McpServerConfig = {"command": command}
    if isinstance(args, list):
        result["args"] = list(args)
    if isinstance(env, dict):
        result["env"] = dict(env)
    return result


def _validate_agents(value: dict) -> dict:
    if not isinstance(value, dict):
        raise ValueError("agents must be an object")
    result = {}
    for name, entry in value.items():
        if not isinstance(entry, dict):
            raise ValueError(f"agents.{name} must be an object")
        command = _non_empty_trimmed_string(
            entry.get("command"),
            f"agents.{name}.command must be a non-empty string",
        )
        if command is None:
            raise ValueError(f"agents.{name}.command must be a non-empty string")
        agent_entry: AcpxAgentEntry = {"command": command}
        args = entry.get("args")
        if args is not None:
            if not isinstance(args, list) or not all(isinstance(a, str) for a in args):
                raise ValueError(f"agents.{name}.args must be an array of strings")
            agent_entry["args"] = list(args)
        result[name] = agent_entry
    return result


def parse_acpx_plugin_config(value) -> AcpxPluginConfig:
    if value is None:
        return {}
    if not isinstance(value, dict):
        raise ValueError("acpx plugin config must be an object")
    result: AcpxPluginConfig = {}
    cwd = _non_empty_trimmed_string(value.get("cwd"), "cwd must be a non-empty string")
    if cwd is not None:
        result["cwd"] = cwd
    state_dir = _non_empty_trimmed_string(value.get("stateDir"), "stateDir must be a non-empty string")
    if state_dir is not None:
        result["stateDir"] = state_dir
    probe_agent = _non_empty_trimmed_string(value.get("probeAgent"), "probeAgent must be a non-empty string")
    if probe_agent is not None:
        result["probeAgent"] = probe_agent
    permission_mode = value.get("permissionMode")
    if permission_mode is not None:
        if not isinstance(permission_mode, str) or permission_mode not in _VALID_PERMISSION_MODES:
            raise ValueError(f"permissionMode must be one of: {', '.join(ACPX_PERMISSION_MODES)}")
        result["permissionMode"] = permission_mode
    non_interactive = value.get("nonInteractivePermissions")
    if non_interactive is not None:
        if not isinstance(non_interactive, str) or non_interactive not in _VALID_NON_INTERACTIVE_POLICIES:
            raise ValueError(f"nonInteractivePermissions must be one of: {', '.join(ACPX_NON_INTERACTIVE_POLICIES)}")
        result["nonInteractivePermissions"] = non_interactive
    for bool_key in ("pluginToolsMcpBridge", "openClawToolsMcpBridge", "strictWindowsCmdWrapper"):
        bool_value = value.get(bool_key)
        if bool_value is not None:
            if not isinstance(bool_value, bool):
                raise ValueError(f"{bool_key} must be a boolean")
            result[bool_key] = bool_value
    timeout_seconds = value.get("timeoutSeconds")
    if timeout_seconds is not None:
        if not isinstance(timeout_seconds, (int, float)) or isinstance(timeout_seconds, bool) or timeout_seconds < 0.001:
            raise ValueError("timeoutSeconds must be a number >= 0.001")
        result["timeoutSeconds"] = float(timeout_seconds)
    queue_owner_ttl = value.get("queueOwnerTtlSeconds")
    if queue_owner_ttl is not None:
        if not isinstance(queue_owner_ttl, (int, float)) or isinstance(queue_owner_ttl, bool) or queue_owner_ttl < 0:
            raise ValueError("queueOwnerTtlSeconds must be a number >= 0")
        result["queueOwnerTtlSeconds"] = float(queue_owner_ttl)
    mcp_servers = value.get("mcpServers")
    if mcp_servers is not None:
        if not isinstance(mcp_servers, dict):
            raise ValueError("mcpServers must be an object")
        validated = {}
        for name, server in mcp_servers.items():
            validated[name] = _validate_mcp_server_config(name, server)
        result["mcpServers"] = validated
    agents = value.get("agents")
    if agents is not None:
        result["agents"] = _validate_agents(agents)
    return result


ACPX_PLUGIN_TOOLS_MCP_SERVER_NAME = "openclaw-plugin-tools"
ACPX_OPENCLAW_TOOLS_MCP_SERVER_NAME = "openclaw-tools"
