"""Tests for the codex-supervisor extension entry."""

from __future__ import annotations

from openclaw.plugin_sdk.plugin_test_runtime import create_captured_plugin_registration
from openclaw_extensions.codex_supervisor import index


def test_registers_supervisor_tools_from_plugin_config() -> None:
    captured = create_captured_plugin_registration(id="codex-supervisor")
    captured.api.plugin_config = {
        "endpoints": [
            {
                "id": "test",
                "transport": "websocket",
                "url": "ws://127.0.0.1:12345",
            }
        ],
        "allowRawTranscripts": True,
        "allowWriteControls": True,
    }

    index.default.register(captured.api)

    assert sorted(tool["name"] for tool in captured.tools) == [
        "codex_endpoint_probe",
        "codex_session_interrupt",
        "codex_session_read",
        "codex_session_send",
        "codex_sessions_list",
    ]
    assert len(captured.runtime_lifecycles) == 1
    assert captured.runtime_lifecycles[0]["id"] == "codex-supervisor"
    assert (
        captured.runtime_lifecycles[0]["description"]
        == "Close Codex supervisor app-server connections."
    )
    schema = index.default.config_schema["jsonSchema"]
    assert schema["type"] == "object"
    properties = schema["properties"]
    assert properties["endpoints"]["type"] == "array"
    assert properties["allowRawTranscripts"] == {"type": "boolean", "default": False}
    assert properties["allowWriteControls"] == {"type": "boolean", "default": False}
