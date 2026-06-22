"""Tests for abortable helper."""

from __future__ import annotations

import asyncio

import pytest

from openclaw.agents.embedded_agent_runner.run.abortable import AbortError, abortable


@pytest.mark.asyncio
async def test_aborts_before_inner_settles():
    event = asyncio.Event()
    inner = asyncio.get_event_loop().create_future()
    wrapped = abortable(event, inner)
    event.set()
    with pytest.raises(AbortError):
        await wrapped


@pytest.mark.asyncio
async def test_rejects_when_already_aborted():
    event = asyncio.Event()
    event.set()
    inner = asyncio.get_event_loop().create_future()
    with pytest.raises(AbortError, match="aborted"):
        await abortable(event, inner)


@pytest.mark.asyncio
async def test_resolves_when_inner_completes_first():
    async def inner() -> int:
        return 42

    assert await abortable(None, inner()) == 42