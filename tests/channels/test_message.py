"""Tests for channels/message — adapter, capabilities, state."""

from __future__ import annotations

from openclaw.channels.message import (
    classify_durable_send_recovery_state,
    create_durable_message_state_record,
    define_channel_message_adapter,
    derive_durable_final_delivery_requirements,
)


class TestAdapter:
    def test_defaults_receive_to_manual(self):
        adapter = define_channel_message_adapter({"name": "test"})
        assert adapter["receive"]["defaultAckPolicy"] == "manual"
        assert "manual" in adapter["receive"]["supportedAckPolicies"]

    def test_preserves_existing_receive(self):
        adapter = define_channel_message_adapter({
            "name": "test",
            "receive": {"defaultAckPolicy": "auto", "supportedAckPolicies": ["auto", "manual"]},
        })
        assert adapter["receive"]["defaultAckPolicy"] == "auto"


class TestCapabilities:
    def test_text_always_required(self):
        reqs = derive_durable_final_delivery_requirements({"payload": {}})
        assert reqs["text"] is True

    def test_media_required_when_mediaUrl(self):
        reqs = derive_durable_final_delivery_requirements({
            "payload": {"mediaUrl": "https://example.com/img.png"},
        })
        assert reqs["media"] is True

    def test_media_not_required_without_media(self):
        reqs = derive_durable_final_delivery_requirements({"payload": {}})
        assert "media" not in reqs

    def test_reply_to_required(self):
        reqs = derive_durable_final_delivery_requirements({
            "payload": {},
            "replyToId": "msg-123",
        })
        assert reqs["replyTo"] is True

    def test_thread_required(self):
        reqs = derive_durable_final_delivery_requirements({"payload": {}, "threadId": 42})
        assert reqs["thread"] is True

    def test_silent_required(self):
        reqs = derive_durable_final_delivery_requirements({"payload": {}, "silent": True})
        assert reqs["silent"] is True

    def test_extra_capabilities(self):
        reqs = derive_durable_final_delivery_requirements({
            "payload": {},
            "extraCapabilities": {"custom": True},
        })
        assert reqs["custom"] is True


class TestState:
    def test_create_pending(self):
        record = create_durable_message_state_record({"text": "hello"})
        assert record["state"] == "pending"
        assert record["updatedAt"] > 0

    def test_create_sent_with_receipt(self):
        record = create_durable_message_state_record(
            {"text": "hello"},
            receipt={"messageId": "m1"},
        )
        assert record["state"] == "sent"
        assert record["receipt"]["messageId"] == "m1"

    def test_create_with_error(self):
        record = create_durable_message_state_record(
            {"text": "hello"},
            error=ValueError("send failed"),
        )
        assert "send failed" in record["errorMessage"]

    def test_classify_failed(self):
        assert classify_durable_send_recovery_state(failed=True) == "failed"

    def test_classify_suppressed(self):
        assert classify_durable_send_recovery_state(suppressed=True) == "suppressed"

    def test_classify_sent(self):
        assert classify_durable_send_recovery_state(has_receipt=True) == "sent"

    def test_classify_unknown_after_send(self):
        assert classify_durable_send_recovery_state(
            has_intent=True,
            platform_send_may_have_started=True,
        ) == "unknown_after_send"

    def test_classify_pending(self):
        assert classify_durable_send_recovery_state() == "pending"
