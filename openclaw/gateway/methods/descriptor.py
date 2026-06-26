"""Gateway method descriptor types define the reusable contract shared by core,
plugin, channel, and auxiliary methods.

Mirrors src/gateway/methods/descriptor.ts.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Callable, Literal, TypedDict, Union

NODE_GATEWAY_METHOD_SCOPE: str = "node"
DYNAMIC_GATEWAY_METHOD_SCOPE: str = "dynamic"

GatewayMethodScope = str  # OperatorScope | "node" | "dynamic"
GatewayMethodStartupAvailability = Literal["available", "unavailable-until-sidecars"]
GatewayMethodHandler = Callable[..., Any]


class GatewayMethodOwnerCore(TypedDict):
    kind: Literal["core"]
    area: str


class GatewayMethodOwnerPlugin(TypedDict):
    kind: Literal["plugin"]
    pluginId: str


class GatewayMethodOwnerChannel(TypedDict):
    kind: Literal["channel"]
    channelId: str


class GatewayMethodOwnerAux(TypedDict):
    kind: Literal["aux"]
    area: str


GatewayMethodOwner = Union[
    GatewayMethodOwnerCore,
    GatewayMethodOwnerPlugin,
    GatewayMethodOwnerChannel,
    GatewayMethodOwnerAux,
]


@dataclass
class GatewayMethodDescriptor:
    """Complete metadata for one dispatchable gateway method."""

    name: str
    handler: GatewayMethodHandler
    scope: str
    owner: dict[str, Any]
    startup: str | None = None
    control_plane_write: bool = False
    advertise: bool = False
    description: str | None = None


@dataclass
class GatewayMethodRegistryView:
    """Read-only method registry view used by request dispatch and method listing."""

    get_handler: Callable[[str], GatewayMethodHandler | None] = field(default=lambda _: None)
    list_methods: Callable[[], list[str]] = field(default=lambda: [])
    list_advertised_methods: Callable[[], list[str]] = field(default=lambda: [])
    get_scope: Callable[[str], str | None] = field(default=lambda _: None)
    is_startup_unavailable: Callable[[str], bool] = field(default=lambda _: False)
    is_control_plane_write: Callable[[str], bool] = field(default=lambda _: False)
    descriptors: Callable[[], list[GatewayMethodDescriptor]] = field(default=lambda: [])
