"""Tests for gateway/methods descriptor types."""

from openclaw.gateway.methods.descriptor import (
    NODE_GATEWAY_METHOD_SCOPE,
    DYNAMIC_GATEWAY_METHOD_SCOPE,
    GatewayMethodDescriptor,
    GatewayMethodRegistryView,
)


def test_scope_constants():
    assert NODE_GATEWAY_METHOD_SCOPE == "node"
    assert DYNAMIC_GATEWAY_METHOD_SCOPE == "dynamic"


def test_descriptor_creation():
    d = GatewayMethodDescriptor(
        name="ping",
        handler=lambda: "pong",
        scope="node",
        owner={"kind": "core", "area": "system"},
    )
    assert d.name == "ping"
    assert d.scope == "node"
    assert d.owner["kind"] == "core"
    assert d.startup is None
    assert d.control_plane_write is False
    assert d.advertise is False


def test_descriptor_with_all_fields():
    d = GatewayMethodDescriptor(
        name="agent.run",
        handler=lambda: None,
        scope="dynamic",
        owner={"kind": "plugin", "pluginId": "agent"},
        startup="unavailable-until-sidecars",
        control_plane_write=True,
        advertise=True,
        description="Run an agent",
    )
    assert d.startup == "unavailable-until-sidecars"
    assert d.control_plane_write is True
    assert d.advertise is True
    assert d.description == "Run an agent"


def test_registry_view_defaults():
    view = GatewayMethodRegistryView()
    assert view.get_handler("x") is None
    assert view.list_methods() == []
    assert view.list_advertised_methods() == []
    assert view.get_scope("x") is None
    assert view.is_startup_unavailable("x") is False
    assert view.is_control_plane_write("x") is False
    assert view.descriptors() == []


def test_registry_view_custom():
    handler = lambda: "ok"
    view = GatewayMethodRegistryView(
        get_handler=lambda n: handler if n == "ping" else None,
        list_methods=lambda: ["ping"],
        list_advertised_methods=lambda: ["ping"],
        get_scope=lambda n: "node" if n == "ping" else None,
        is_startup_unavailable=lambda n: False,
        is_control_plane_write=lambda n: True,
        descriptors=lambda: [
            GatewayMethodDescriptor(
                name="ping", handler=handler, scope="node",
                owner={"kind": "core", "area": "system"},
            )
        ],
    )
    assert view.get_handler("ping") is handler
    assert view.list_methods() == ["ping"]
    assert view.get_scope("ping") == "node"
    assert view.is_control_plane_write("ping") is True
    descs = view.descriptors()
    assert len(descs) == 1
    assert descs[0].name == "ping"


def test_owner_variants():
    owners = [
        {"kind": "core", "area": "system"},
        {"kind": "plugin", "pluginId": "x"},
        {"kind": "channel", "channelId": "discord"},
        {"kind": "aux", "area": "tools"},
    ]
    for owner in owners:
        d = GatewayMethodDescriptor(
            name="m", handler=lambda: None, scope="dynamic", owner=owner
        )
        assert d.owner["kind"] in ("core", "plugin", "channel", "aux")
