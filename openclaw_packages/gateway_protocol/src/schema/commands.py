from typing import Optional, List, Any

class Command:
    command_id: str
    name: str
    description: Optional[str]
    plugin_id: Optional[str]
    metadata: Optional[dict]

class CommandsListParams:
    plugin_id: Optional[str]
    metadata: Optional[dict]

class CommandsListResult:
    commands: List[Command]
    metadata: Optional[dict]
