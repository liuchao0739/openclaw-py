"""Tests for auto_reply/reply/queue — types, state, settings, normalize, enqueue, directive, drain, cleanup."""

from __future__ import annotations

import time

import pytest

from openclaw.auto_reply.reply.queue.cleanup import (
    clear_all_queues,
    get_queue_stats,
    prune_stale_queues,
)
from openclaw.auto_reply.reply.queue.directive import (
    extract_queue_directive,
    resolve_queue_mode,
)
from openclaw.auto_reply.reply.queue.drain import has_queued_followups
from openclaw.auto_reply.reply.queue.enqueue import (
    clear_session_queue,
    dequeue_followup,
    enqueue_followup,
    peek_followup,
)
from openclaw.auto_reply.reply.queue.normalize import (
    apply_drop_policy,
    dedupe_queue,
    normalize_followup_run,
)
from openclaw.auto_reply.reply.queue.settings import (
    DEFAULT_QUEUE_SETTINGS,
    normalize_queue_settings,
    resolve_queue_settings,
)
from openclaw.auto_reply.reply.queue.state import (
    get_queue_state,
    reset_queue_state_for_tests,
)
from openclaw.auto_reply.reply.queue.types import (
    FollowupRunDeferredError,
    is_followup_run_deferred_error,
)


@pytest.fixture(autouse=True)
def _reset_state():
    reset_queue_state_for_tests()
    yield
    reset_queue_state_for_tests()


class TestTypes:
    def test_followup_run_deferred_error(self):
        err = FollowupRunDeferredError()
        assert is_followup_run_deferred_error(err) is True
        assert is_followup_run_deferred_error(ValueError("other")) is False

    def test_deferred_error_custom_message(self):
        err = FollowupRunDeferredError("custom")
        assert "custom" in str(err)


class TestState:
    def test_empty_queue(self):
        state = get_queue_state()
        assert state.get_queue("s1") == []
        assert state.has_pending("s1") is False

    def test_set_and_clear(self):
        state = get_queue_state()
        state.set_queue("s1", [{"prompt": "hello"}])
        assert state.has_pending("s1") is True
        cleared = state.clear_queue("s1")
        assert cleared == [{"prompt": "hello"}]
        assert state.has_pending("s1") is False

    def test_active_run(self):
        state = get_queue_state()
        state.set_active_run("s1", {"prompt": "running"})
        assert state.get_active_run("s1") == {"prompt": "running"}
        state.set_active_run("s1", None)
        assert state.get_active_run("s1") is None


class TestSettings:
    def test_defaults(self):
        settings = resolve_queue_settings(None)
        assert settings["mode"] == "followup"
        assert settings["debounceMs"] == 500
        assert settings["cap"] == 10

    def test_from_config(self):
        config = {"autoReply": {"queue": {"mode": "steer", "cap": 5}}}
        settings = resolve_queue_settings(config)
        assert settings["mode"] == "steer"
        assert settings["cap"] == 5

    def test_normalize_invalid(self):
        settings = normalize_queue_settings({"debounceMs": -1, "cap": 0})
        assert settings["debounceMs"] == 0
        assert settings["cap"] == 1


class TestNormalize:
    def test_normalize_run(self):
        run = normalize_followup_run({"prompt": "  hello  "})
        assert run["prompt"] == "hello"
        assert "enqueuedAt" in run

    def test_dedupe_message_id(self):
        queue = [
            {"messageId": "m1", "prompt": "a"},
            {"messageId": "m1", "prompt": "b"},
            {"messageId": "m2", "prompt": "c"},
        ]
        result = dedupe_queue(queue, "message-id")
        assert len(result) == 2

    def test_dedupe_prompt(self):
        queue = [
            {"prompt": "hello"},
            {"prompt": "hello"},
            {"prompt": "world"},
        ]
        result = dedupe_queue(queue, "prompt")
        assert len(result) == 2

    def test_dedupe_none(self):
        queue = [{"prompt": "a"}, {"prompt": "a"}]
        result = dedupe_queue(queue, "none")
        assert len(result) == 2

    def test_drop_policy_old(self):
        queue = [{"prompt": str(i)} for i in range(5)]
        result = apply_drop_policy(queue, cap=3, policy="old")
        assert len(result) == 3
        assert result[0]["prompt"] == "2"  # keeps tail

    def test_drop_policy_new(self):
        queue = [{"prompt": str(i)} for i in range(5)]
        result = apply_drop_policy(queue, cap=3, policy="new")
        assert len(result) == 3
        assert result[0]["prompt"] == "0"  # keeps head


class TestEnqueue:
    def test_enqueue_and_dequeue(self):
        enqueue_followup("s1", {"prompt": "hello"})
        assert has_queued_followups("s1") is True

        run = dequeue_followup("s1")
        assert run is not None
        assert run["prompt"] == "hello"
        assert has_queued_followups("s1") is False

    def test_peek(self):
        enqueue_followup("s1", {"prompt": "first"})
        enqueue_followup("s1", {"prompt": "second"})
        run = peek_followup("s1")
        assert run["prompt"] == "first"
        assert has_queued_followups("s1") is True

    def test_clear(self):
        enqueue_followup("s1", {"prompt": "hello"})
        cleared = clear_session_queue("s1")
        assert len(cleared) == 1
        assert has_queued_followups("s1") is False

    def test_dequeue_empty(self):
        assert dequeue_followup("s1") is None


class TestDirective:
    def test_no_directive(self):
        result = extract_queue_directive("hello world")
        assert result["hasDirective"] is False
        assert result["mode"] is None

    def test_steer(self):
        result = extract_queue_directive("hello /steer world")
        assert result["hasDirective"] is True
        assert result["mode"] == "steer"
        assert "hello" in result["cleaned"]
        assert "world" in result["cleaned"]

    def test_followup(self):
        result = extract_queue_directive("/followup do something")
        assert result["mode"] == "followup"

    def test_collect(self):
        result = extract_queue_directive("/collect task")
        assert result["mode"] == "collect"

    def test_interrupt(self):
        result = extract_queue_directive("/interrupt now")
        assert result["mode"] == "interrupt"

    def test_resolve_mode_default(self):
        assert resolve_queue_mode("hello") == "followup"

    def test_resolve_mode_from_directive(self):
        assert resolve_queue_mode("/steer task") == "steer"


class TestCleanup:
    def test_clear_all(self):
        enqueue_followup("s1", {"prompt": "a"})
        enqueue_followup("s2", {"prompt": "b"})
        count = clear_all_queues()
        assert count >= 2
        assert not has_queued_followups("s1")

    def test_get_stats(self):
        enqueue_followup("s1", {"prompt": "a"})
        enqueue_followup("s1", {"prompt": "b"})
        stats = get_queue_stats()
        assert stats["totalSessions"] >= 1
        assert stats["totalPending"] >= 2

    def test_prune_stale(self):
        # Enqueue with old timestamp
        old_time = int(time.time() * 1000) - 31 * 60 * 1000
        state = get_queue_state()
        state.set_queue("stale", [{"prompt": "old", "enqueuedAt": old_time}])
        pruned = prune_stale_queues()
        assert pruned >= 1
        assert not has_queued_followups("stale")
