"""Integration tests for remaining MVP modules."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from openclaw.auto_reply.router import route_inbound
from openclaw.channels.base import InboundMessage
from openclaw.channels.web import WebChannel
from openclaw.gateway.server import create_app
from openclaw.media.files import load_attachment, save_attachment
from openclaw.mcp.bridge import McpBridge, McpTool
from openclaw.plugin_sdk.manifest import load_plugin_manifest
from openclaw.plugins.loader import discover_plugins
from openclaw.skills.executor import SkillExecutor
from openclaw.skills.loader import discover_skills, load_skill
from openclaw.storage.agent_db import agent_db_path, init_agent_db
from openclaw.storage.state_db import init_state_db, state_db_path


def test_load_telegram_manifest(ts_repo: Path) -> None:
    manifest = load_plugin_manifest(str(ts_repo / "extensions/telegram"))
    assert manifest.id == "telegram"
    assert "telegram" in manifest.channels


def test_discover_plugins_from_openclaw_repo(ts_repo: Path) -> None:
    plugins = discover_plugins(str(ts_repo / "extensions"))
    assert any(plugin.id == "telegram" for plugin in plugins)


def test_load_weather_skill(ts_repo: Path) -> None:
    skill = load_skill(str(ts_repo / "skills/weather/SKILL.md"))
    assert skill.name == "weather"
    assert "weather" in skill.description.lower()


def test_discover_skills_from_openclaw_repo(ts_repo: Path) -> None:
    skills = discover_skills(str(ts_repo / "skills"))
    assert any(skill.name == "weather" for skill in skills)


def test_skill_executor(ts_repo: Path) -> None:
    skill = load_skill(str(ts_repo / "skills/weather/SKILL.md"))
    executor = SkillExecutor()
    executor.register(skill.name, lambda s, prompt: f"{s.name}:{prompt}")
    assert executor.execute(skill, "forecast") == "weather:forecast"


@pytest.mark.asyncio
async def test_auto_reply_router() -> None:
    async def handler(message: InboundMessage) -> str:
        return f"reply:{message.text}"

    outbound = await route_inbound(
        InboundMessage(channel_id="web", sender_id="u1", text="hi"),
        handler,
    )
    assert outbound.text == "reply:hi"


@pytest.mark.asyncio
async def test_web_channel_roundtrip() -> None:
    from openclaw.channels.base import OutboundMessage

    channel = WebChannel()
    await channel.enqueue_inbound("u1", "hello")
    inbound = await channel.receive()
    assert inbound is not None
    await channel.send(
        OutboundMessage(channel_id="web", target_id=inbound.sender_id, text="pong")
    )
    outbound = await channel.drain_outbound()
    assert outbound[0].text == "pong"


@pytest.mark.asyncio
async def test_mcp_bridge_call() -> None:
    bridge = McpBridge(server_name="test")
    bridge.register_tool(McpTool(name="echo", description="echo"))
    result = await bridge.call_tool("echo", {"text": "hi"})
    assert result["tool"] == "echo"


def test_state_and_agent_db(tmp_path: Path) -> None:
    init_state_db(str(tmp_path))
    init_agent_db(str(tmp_path), "main")
    assert state_db_path(str(tmp_path)).exists()
    assert agent_db_path(str(tmp_path), "main").exists()


def test_media_attachment_roundtrip(tmp_path: Path) -> None:
    source = tmp_path / "sample.txt"
    source.write_text("hello", encoding="utf-8")
    attachment = load_attachment(source)
    target = save_attachment(tmp_path / "out" / attachment.filename, attachment)
    assert target.read_text(encoding="utf-8") == "hello"


def test_gateway_chat_e2e() -> None:
    client = TestClient(create_app())
    response = client.post(
        "/v1/chat",
        json={"messages": [{"role": "user", "content": "ping"}]},
    )
    assert response.status_code == 200
    assert "ping" in response.json()["message"]["content"]
