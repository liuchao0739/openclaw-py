"""Tests for ACP control-plane modules."""

import asyncio

from openclaw.acp.control_plane import (
    SessionActorQueue,
    mark_acp_turn_active,
    clear_acp_turn_active,
    is_acp_turn_active,
    reset_acp_active_turns_for_tests,
    get_acp_session_manager,
    reset_acp_session_manager_for_tests,
)


class TestSessionActorQueue:
    def test_serializes_same_key(self):
        queue = SessionActorQueue()
        order = []

        async def task_a():
            order.append("a-start")
            await asyncio.sleep(0.01)
            order.append("a-end")

        async def task_b():
            order.append("b-start")
            await asyncio.sleep(0.01)
            order.append("b-end")

        async def main():
            t1 = asyncio.create_task(queue.run("k", task_a))
            t2 = asyncio.create_task(queue.run("k", task_b))
            await asyncio.gather(t1, t2)

        asyncio.run(main())
        assert order == ["a-start", "a-end", "b-start", "b-end"]

    def test_parallel_different_keys(self):
        queue = SessionActorQueue()
        order = []

        async def task_a():
            order.append("a-start")
            await asyncio.sleep(0.01)
            order.append("a-end")

        async def task_b():
            order.append("b-start")
            await asyncio.sleep(0.01)
            order.append("b-end")

        async def main():
            await asyncio.gather(queue.run("k1", task_a), queue.run("k2", task_b))

        asyncio.run(main())
        # Both can start concurrently since different keys
        assert "a-start" in order[:2]
        assert "b-start" in order[:2]

    def test_pending_count(self):
        queue = SessionActorQueue()
        assert queue.get_total_pending_count() == 0

        async def task():
            assert queue.get_pending_count("k") == 1
            assert queue.get_total_pending_count() == 1
            await asyncio.sleep(0.01)

        asyncio.run(queue.run("k", task))
        assert queue.get_total_pending_count() == 0

    def test_returns_result(self):
        queue = SessionActorQueue()

        async def task():
            return 42

        result = asyncio.run(queue.run("k", task))
        assert result == 42

    def test_propagates_error(self):
        queue = SessionActorQueue()

        async def task():
            raise ValueError("boom")

        try:
            asyncio.run(queue.run("k", task))
            assert False
        except ValueError:
            pass
        assert queue.get_total_pending_count() == 0


class TestActiveTurns:
    def setup_method(self):
        reset_acp_active_turns_for_tests()

    def test_mark_and_check(self):
        assert not is_acp_turn_active("sess-1")
        mark_acp_turn_active("sess-1")
        assert is_acp_turn_active("sess-1")

    def test_clear(self):
        mark_acp_turn_active("sess-1")
        clear_acp_turn_active("sess-1")
        assert not is_acp_turn_active("sess-1")

    def test_case_insensitive(self):
        mark_acp_turn_active("Sess-1")
        assert is_acp_turn_active("sess-1")
        assert is_acp_turn_active(" SESS-1 ")

    def test_empty_key(self):
        mark_acp_turn_active("")
        assert not is_acp_turn_active("")

    def test_clear_nonexistent(self):
        clear_acp_turn_active("nonexistent")

    def test_reset(self):
        mark_acp_turn_active("a")
        mark_acp_turn_active("b")
        reset_acp_active_turns_for_tests()
        assert not is_acp_turn_active("a")
        assert not is_acp_turn_active("b")


class TestAcpSessionManager:
    def setup_method(self):
        reset_acp_session_manager_for_tests()

    def test_singleton(self):
        m1 = get_acp_session_manager()
        m2 = get_acp_session_manager()
        assert m1 is m2

    def test_initialize_session(self):
        mgr = get_acp_session_manager()
        result = asyncio.run(mgr.initialize_session({
            "sessionKey": "s1",
            "agent": "assistant",
            "mode": "interactive",
        }))
        assert result["sessionKey"] == "s1"
        assert result["state"] == "ready"

    def test_run_turn(self):
        mgr = get_acp_session_manager()
        result = asyncio.run(mgr.run_turn({
            "sessionKey": "s1",
            "text": "hello",
        }))
        assert result["sessionKey"] == "s1"
        assert result["text"] == "hello"

    def test_close_session(self):
        mgr = get_acp_session_manager()
        asyncio.run(mgr.initialize_session({"sessionKey": "s1", "agent": "a"}))
        result = asyncio.run(mgr.close_session({"sessionKey": "s1", "discardPersistentState": True}))
        assert result["runtimeClosed"] is True
        assert result["metaCleared"] is True

    def test_close_nonexistent(self):
        mgr = get_acp_session_manager()
        result = asyncio.run(mgr.close_session({"sessionKey": "nope"}))
        assert result["runtimeClosed"] is False

    def test_observability(self):
        mgr = get_acp_session_manager()
        snap = mgr.get_observability_snapshot()
        assert "turns" in snap
        assert snap["turns"]["completed"] == 0

    def test_observability_after_turn(self):
        mgr = get_acp_session_manager()
        asyncio.run(mgr.run_turn({"sessionKey": "s1", "text": "hi"}))
        snap = mgr.get_observability_snapshot()
        assert snap["turns"]["completed"] == 1
        assert snap["turns"]["averageLatencyMs"] > 0
