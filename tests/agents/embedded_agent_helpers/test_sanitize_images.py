"""sanitize-user-facing-text and images helpers."""

import asyncio

from openclaw.agents.embedded_agent_helpers.images import (
    is_empty_assistant_message_content,
    sanitize_session_messages_images,
)
from openclaw.agents.embedded_agent_helpers.sanitize_user_facing_text import (
    format_billing_error_message,
    format_transport_error_copy,
    is_streaming_json_parse_error,
    sanitize_user_facing_text,
)

def test_billing_oauth_copy():
    msg = format_billing_error_message(provider="anthropic", auth_mode="oauth")
    assert "subscription" in msg.lower()


def test_transport_connection_refused():
    assert "connection refused" in (format_transport_error_copy("ECONNREFUSED") or "")


def test_sanitize_billing_error_context():
    out = sanitize_user_facing_text("Error: payment required", error_context=True)
    assert "billing" in out.lower() or "⚠️" in out


def test_empty_assistant():
    assert is_empty_assistant_message_content({"role": "assistant", "content": []})


def test_sanitize_session_messages():
    msgs = [{"role": "assistant", "content": []}]
    out = asyncio.run(sanitize_session_messages_images(msgs, "test"))
    assert out[0]["content"]