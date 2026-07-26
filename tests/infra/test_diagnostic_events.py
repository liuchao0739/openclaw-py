"""Tests for diagnostic event dispatcher helpers."""

from __future__ import annotations

import pytest

from openclaw.infra.diagnostic_events import (
    emit_diagnostic_event,
    on_diagnostic_event,
    reset_diagnostic_events_for_test,
    wait_for_diagnostic_events_drained,
)


@pytest.fixture(autouse=True)
def _reset_events() -> None:
    reset_diagnostic_events_for_test()


def test_on_diagnostic_event_receives_untrusted_events() -> None:
    seen: list[dict[str, object]] = []

    unsubscribe = on_diagnostic_event(lambda event: seen.append(dict(event)))
    emit_diagnostic_event({"type": "tool.loop", "count": 1})

    assert len(seen) == 1
    assert seen[0]["type"] == "tool.loop"
    assert seen[0]["count"] == 1
    assert "seq" in seen[0]
    assert "ts" in seen[0]
    unsubscribe()


@pytest.mark.asyncio
async def test_async_diagnostic_events_are_drained() -> None:
    seen: list[str] = []

    unsubscribe = on_diagnostic_event(lambda event: seen.append(str(event.get("type"))))
    emit_diagnostic_event({"type": "model.call.completed", "provider": "test"})
    await wait_for_diagnostic_events_drained()

    assert seen == ["model.call.completed"]
    unsubscribe()
