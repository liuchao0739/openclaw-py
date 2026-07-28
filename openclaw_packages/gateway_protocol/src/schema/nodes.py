from typing import Literal, Final, Optional, List, Any

NODE_KIND = Literal["managed", "unmanaged"]

NODE_KIND_MANAGED: Literal["managed"] = "managed"
NODE_KIND_UNMANAGED: Literal["unmanaged"] = "unmanaged"

NODE_KINDS: Final[tuple] = (
    NODE_KIND_MANAGED,
    NODE_KIND_UNMANAGED,
)

NODE_STATE = Literal["attached", "detached", "offline", "online", "unreachable"]

NODE_STATE_ATTACHED: Literal["attached"] = "attached"
NODE_STATE_DETACHED: Literal["detached"] = "detached"
NODE_STATE_OFFLINE: Literal["offline"] = "offline"
NODE_STATE_ONLINE: Literal["online"] = "online"
NODE_STATE_UNREACHABLE: Literal["unreachable"] = "unreachable"

NODE_STATES: Final[tuple] = (
    NODE_STATE_ATTACHED,
    NODE_STATE_DETACHED,
    NODE_STATE_OFFLINE,
    NODE_STATE_ONLINE,
    NODE_STATE_UNREACHABLE,
)

class Node:
    node_id: str
    kind: NODE_KIND
    state: NODE_STATE
    name: Optional[str]
    metadata: Optional[dict]

class NodesGetParams:
    node_id: Optional[str]
    metadata: Optional[dict]

class NodesGetResult:
    node: Optional[Node]
    metadata: Optional[dict]

class NodesListParams:
    metadata: Optional[dict]

class NodesListResult:
    nodes: List[Node]
    metadata: Optional[dict]

class NodesAttachParams:
    node_id: str
    metadata: Optional[dict]

class NodesAttachResult:
    node_id: str
    metadata: Optional[dict]

class NodesDetachParams:
    node_id: str
    metadata: Optional[dict]

class NodesDetachResult:
    node_id: str
    metadata: Optional[dict]
