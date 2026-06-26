"""Tests for context-engine registry, legacy engine, and init."""

import pytest

from openclaw.context_engine.registry import (
    ContextEngineRegistryError,
    ContextEngineNotRegisteredError,
    registerContextEngineForOwner,
    resolveContextEngine,
    _reset_registry_for_tests,
)
from openclaw.context_engine.legacy import LegacyContextEngine
from openclaw.context_engine.legacy_registration import register_legacy_context_engine
from openclaw.context_engine.init import (
    ensureContextEnginesInitialized,
    _reset_init_for_tests,
)


@pytest.fixture(autouse=True)
def _clean():
    _reset_registry_for_tests()
    _reset_init_for_tests()
    yield
    _reset_registry_for_tests()
    _reset_init_for_tests()


async def _make_legacy():
    return LegacyContextEngine()


async def _make_other():
    return LegacyContextEngine()


def test_register_and_resolve():
    registerContextEngineForOwner("legacy", _make_legacy, "core")
    engine, owner = __import__("asyncio").run(resolveContextEngine("legacy"))
    assert isinstance(engine, LegacyContextEngine)
    assert owner == "core"


def test_resolve_unknown_raises():
    with pytest.raises(ContextEngineNotRegisteredError):
        __import__("asyncio").run(resolveContextEngine("nope"))


def test_duplicate_same_owner_without_refresh_raises():
    registerContextEngineForOwner("legacy", _make_legacy, "core")
    with pytest.raises(ContextEngineRegistryError):
        registerContextEngineForOwner("legacy", _make_other, "core")


def test_duplicate_same_owner_with_refresh_ok():
    registerContextEngineForOwner(
        "legacy", _make_legacy, "core", allowSameOwnerRefresh=True
    )
    registerContextEngineForOwner(
        "legacy", _make_other, "core", allowSameOwnerRefresh=True
    )


def test_duplicate_different_owner_raises():
    registerContextEngineForOwner(
        "legacy", _make_legacy, "core", allowSameOwnerRefresh=True
    )
    with pytest.raises(ContextEngineRegistryError):
        registerContextEngineForOwner("legacy", _make_other, "plugin-x")


def test_resolve_caches_factory():
    calls = {"n": 0}

    async def _factory():
        calls["n"] += 1
        return LegacyContextEngine()

    registerContextEngineForOwner("legacy", _factory, "core")
    import asyncio
    e1, _ = asyncio.run(resolveContextEngine("legacy"))
    e2, _ = asyncio.run(resolveContextEngine("legacy"))
    assert e1 is e2
    assert calls["n"] == 1


def test_legacy_engine_assemble_context():
    import asyncio
    eng = LegacyContextEngine()
    msgs = [{"role": "user", "content": "hi"}]
    out = asyncio.run(eng.assemble_context(msgs))
    assert out == msgs
    # returns a copy
    out.append({"role": "assistant"})
    assert len(msgs) == 1


def test_legacy_engine_assemble_empty():
    import asyncio
    eng = LegacyContextEngine()
    assert asyncio.run(eng.assemble_context(None)) == []
    assert asyncio.run(eng.assemble_context([])) == []


def test_legacy_engine_health():
    import asyncio
    eng = LegacyContextEngine()
    h = asyncio.run(eng.health())
    assert h["name"] == "legacy"
    assert h["healthy"] is True


def test_register_legacy_context_engine():
    register_legacy_context_engine()
    import asyncio
    engine, owner = asyncio.run(resolveContextEngine("legacy"))
    assert isinstance(engine, LegacyContextEngine)
    assert owner == "core"


def test_register_legacy_can_refresh():
    register_legacy_context_engine()
    # should not raise
    register_legacy_context_engine()


def test_ensure_init_idempotent():
    ensureContextEnginesInitialized()
    ensureContextEnginesInitialized()
    import asyncio
    engine, owner = asyncio.run(resolveContextEngine("legacy"))
    assert owner == "core"
