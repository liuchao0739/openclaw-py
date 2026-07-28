from typing import Literal, Final, Optional, List
from enum import Enum

class GatewayClientId(str, Enum):
    WEBCHAT_UI = "webchat-ui"
    CONTROL_UI = "openclaw-control-ui"
    TUI = "openclaw-tui"
    CLI = "openclaw-cli"
    NODE = "openclaw-node"
    GATEWAY = "openclaw-gateway"
    PROBE = "openclaw-probe"
    AGENT = "openclaw-agent"
    EXTERNAL = "external"

GATEWAY_CLIENT_IDS: Final[tuple] = tuple(e.value for e in GatewayClientId)

class GatewayClientMode(str, Enum):
    INTERACTIVE = "interactive"
    SERVICE = "service"
    PROBE = "probe"
    AGENT = "agent"
    EXTERNAL = "external"

GATEWAY_CLIENT_MODES: Final[tuple] = tuple(e.value for e in GatewayClientMode)

GATEWAY_CLIENT_NAMES: Final[dict] = {
    GatewayClientId.WEBCHAT_UI.value: "OpenClaw WebChat UI",
    GatewayClientId.CONTROL_UI.value: "OpenClaw Control UI",
    GatewayClientId.TUI.value: "OpenClaw TUI",
    GatewayClientId.CLI.value: "OpenClaw CLI",
    GatewayClientId.NODE.value: "OpenClaw Node",
    GatewayClientId.GATEWAY.value: "OpenClaw Gateway",
    GatewayClientId.PROBE.value: "OpenClaw Probe",
    GatewayClientId.AGENT.value: "OpenClaw Agent",
    GatewayClientId.EXTERNAL.value: "External Client",
}

class GatewayClientCap(str, Enum):
    CHAT = "chat"
    TALK = "talk"
    COMMANDS = "commands"
    CONFIG = "config"
    CRON = "cron"
    DEVICES = "devices"
    ENVIRONMENTS = "environments"
    EXEC_APPROVALS = "exec-approvals"
    LOGS = "logs"
    NODES = "nodes"
    PLUGIN_APPROVALS = "plugin-approvals"
    PLUGINS = "plugins"
    PUSH = "push"
    SECRETS = "secrets"
    SESSIONS = "sessions"
    TASKS = "tasks"
    WIZARD = "wizard"
    ARTIFACTS = "artifacts"

GATEWAY_CLIENT_CAPS: Final[tuple] = tuple(e.value for e in GatewayClientCap)

GatewayClientName = Literal[
    "OpenClaw WebChat UI",
    "OpenClaw Control UI",
    "OpenClaw TUI",
    "OpenClaw CLI",
    "OpenClaw Node",
    "OpenClaw Gateway",
    "OpenClaw Probe",
    "OpenClaw Agent",
    "External Client",
]

def normalize_gateway_client_id(value: str) -> Optional[GatewayClientId]:
    for member in GatewayClientId:
        if member.value == value:
            return member
    return None

def normalize_gateway_client_mode(value: str) -> Optional[GatewayClientMode]:
    for member in GatewayClientMode:
        if member.value == value:
            return member
    return None

def normalize_gateway_client_name(value: str) -> Optional[str]:
    return GATEWAY_CLIENT_NAMES.get(value)

def has_gateway_client_cap(client_id: GatewayClientId, cap: GatewayClientCap) -> bool:
    return True
