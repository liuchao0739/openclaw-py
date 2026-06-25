"""Tests for channels/turn — delivery result, bot loop, dispatch, history window."""

from __future__ import annotations

from openclaw.channels.turn import (
    apply_history_window,
    clear_channel_bot_pair_loop_guard_for_tests,
    create_channel_delivery_result_from_receipt,
    create_dispatch_result,
    is_delivered,
    is_failed,
    is_suppressed,
    merge_dispatch_results,
    record_channel_bot_pair_loop_and_check_suppression,
    resolve_history_window,
    should_compact_history,
)


class TestDeliveryResult:
    def test_from_receipt(self):
        receipt = {"messageId": "msg-1"}
        result = create_channel_delivery_result_from_receipt(receipt)
        assert result["receipt"]["messageId"] == "msg-1"
        assert result["messageIds"] == ["msg-1"]

    def test_with_thread_and_reply(self):
        result = create_channel_delivery_result_from_receipt(
            {"messageId": "m1"},
            thread_id="t1",
            reply_to_id="r1",
        )
        assert result["threadId"] == "t1"
        assert result["replyToId"] == "r1"

    def test_batch_ids(self):
        receipt = {"messageIds": ["m1", "m2"]}
        result = create_channel_delivery_result_from_receipt(receipt)
        assert "m1" in result["messageIds"]
        assert "m2" in result["messageIds"]


class TestBotLoopProtection:
    def setup_method(self):
        clear_channel_bot_pair_loop_guard_for_tests()

    def test_first_interaction_not_suppressed(self):
        result = record_channel_bot_pair_loop_and_check_suppression(
            "scope1", "conv1", "bot1", "bot2"
        )
        assert result["suppressed"] is False

    def test_suppressed_after_threshold(self):
        for _ in range(5):
            result = record_channel_bot_pair_loop_and_check_suppression(
                "scope1", "conv1", "bot1", "bot2"
            )
        assert result["suppressed"] is True

    def test_disabled(self):
        result = record_channel_bot_pair_loop_and_check_suppression(
            "scope1", "conv1", "bot1", "bot2",
            default_enabled=False,
        )
        assert result["suppressed"] is False


class TestDispatchResult:
    def test_delivered(self):
        result = create_dispatch_result("delivered", message_ids=["m1"])
        assert is_delivered(result) is True
        assert is_failed(result) is False

    def test_failed(self):
        result = create_dispatch_result("failed", error="boom")
        assert is_failed(result) is True

    def test_suppressed(self):
        result = create_dispatch_result("suppressed", suppressed_reason="loop")
        assert is_suppressed(result) is True

    def test_merge_all_delivered(self):
        results = [
            create_dispatch_result("delivered", message_ids=["m1"]),
            create_dispatch_result("delivered", message_ids=["m2"]),
        ]
        merged = merge_dispatch_results(results)
        assert is_delivered(merged) is True
        assert "m1" in merged["messageIds"]

    def test_merge_mixed(self):
        results = [
            create_dispatch_result("delivered", message_ids=["m1"]),
            create_dispatch_result("failed", error="err"),
        ]
        merged = merge_dispatch_results(results)
        assert is_delivered(merged) is True

    def test_merge_empty(self):
        merged = merge_dispatch_results([])
        assert merged["outcome"] == "skipped"


class TestHistoryWindow:
    def test_resolve_default(self):
        assert resolve_history_window() == 50

    def test_resolve_from_config(self):
        cfg = {"agents": {"defaults": {"historyWindow": 100}}}
        assert resolve_history_window(cfg) == 100

    def test_resolve_capped(self):
        cfg = {"agents": {"defaults": {"historyWindow": 500}}}
        assert resolve_history_window(cfg) == 200  # capped at MAX

    def test_apply_window(self):
        messages = [{"text": str(i)} for i in range(100)]
        result = apply_history_window(messages, window=10)
        assert len(result) == 10
        assert result[-1]["text"] == "99"

    def test_apply_window_no_truncation(self):
        messages = [{"text": "a"}]
        assert apply_history_window(messages, window=10) == messages

    def test_should_compact(self):
        messages = [{"text": str(i)} for i in range(45)]
        assert should_compact_history(messages, window=50) is True

    def test_should_not_compact(self):
        messages = [{"text": "a"}]
        assert should_compact_history(messages, window=50) is False
