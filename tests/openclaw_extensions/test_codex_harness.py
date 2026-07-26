"""Tests for Codex agent harness."""

from __future__ import annotations

from openclaw_extensions.codex.harness import create_codex_app_server_agent_harness


def test_supports_the_canonical_codex_virtual_provider() -> None:
    harness = create_codex_app_server_agent_harness()
    assert harness["supports"]({"provider": "codex", "requestedRuntime": "codex"}) == {
        "supported": True,
        "priority": 100,
    }


def test_supports_openai_as_the_primary_openclaw_routing_id() -> None:
    harness = create_codex_app_server_agent_harness()
    assert harness["supports"]({"provider": "openai", "requestedRuntime": "codex"}) == {
        "supported": True,
        "priority": 100,
    }


def test_rejects_providers_codex_app_server_cannot_resolve_from_its_own_config() -> None:
    harness = create_codex_app_server_agent_harness()
    result = harness["supports"]({"provider": "9router", "requestedRuntime": "codex"})
    assert result["supported"] is False
    assert "codex" in (result.get("reason") or "")


def test_normalizes_provider_casing() -> None:
    harness = create_codex_app_server_agent_harness()
    assert harness["supports"]({"provider": "OpenAI", "requestedRuntime": "codex"}) == {
        "supported": True,
        "priority": 100,
    }


def test_honors_explicit_provider_id_overrides() -> None:
    narrow_harness = create_codex_app_server_agent_harness({"providerIds": ["codex"]})
    result = narrow_harness["supports"]({"provider": "openai", "requestedRuntime": "codex"})
    assert result["supported"] is False
