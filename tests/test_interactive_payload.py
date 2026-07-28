from __future__ import annotations

import pytest

from openclaw.interactive.payload import (
    has_interactive_reply_blocks,
    has_message_presentation_blocks,
    has_reply_channel_data,
    has_reply_content,
    has_reply_payload_content,
    interactive_reply_to_presentation,
    normalize_interactive_reply,
    normalize_message_presentation,
    presentation_to_interactive_controls_reply,
    presentation_to_interactive_reply,
    render_message_presentation_fallback_text,
    resolve_interactive_text_fallback,
)


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, False),
        ({}, False),
        ([], False),
        ({"slack": {"blocks": []}}, True),
    ],
)
def test_has_reply_channel_data(value, expected) -> None:
    assert has_reply_channel_data(value) is expected


def test_has_reply_content_treats_whitespace_and_empty_payloads_as_empty() -> None:
    assert (
        has_reply_content(
            {
                "text": "   ",
                "mediaUrls": ["", "   "],
                "interactive": {"blocks": []},
                "hasChannelData": False,
            }
        )
        is False
    )


@pytest.mark.parametrize(
    "input_dict",
    [
        {
            "interactive": {
                "blocks": [
                    {
                        "type": "buttons",
                        "buttons": [{"label": "Retry", "value": "retry"}],
                    }
                ],
            },
        },
        {
            "text": "   ",
            "extraContent": True,
        },
    ],
)
def test_has_reply_content_accepts_interactive_blocks_and_extra(input_dict) -> None:
    assert has_reply_content(input_dict) is True


def test_has_reply_payload_content_trims_text_and_uses_channel_data() -> None:
    assert (
        has_reply_payload_content(
            {
                "text": "   ",
                "channelData": {"slack": {"blocks": []}},
            }
        )
        is True
    )


@pytest.mark.parametrize(
    ("payload", "options"),
    [
        ({"text": "   ", "channelData": {}}, {"hasChannelData": True}),
        ({"text": "   "}, {"extraContent": True}),
    ],
)
def test_has_reply_payload_content_accepts_explicit_overrides(payload, options) -> None:
    assert has_reply_payload_content(payload, options) is True


def test_normalizes_interactive_replies_and_resolves_text_fallback() -> None:
    interactive = normalize_interactive_reply(
        {
            "blocks": [
                {"type": "text", "text": "First"},
                {"type": "buttons", "buttons": [{"label": "Retry", "value": "retry"}]},
                {"type": "text", "text": "Second"},
            ],
        }
    )
    assert interactive == {
        "blocks": [
            {"type": "text", "text": "First"},
            {"type": "buttons", "buttons": [{"label": "Retry", "value": "retry"}]},
            {"type": "text", "text": "Second"},
        ],
    }
    assert resolve_interactive_text_fallback({"interactive": interactive}) == "First\n\nSecond"


def test_preserves_url_only_presentation_buttons() -> None:
    presentation = {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [{"label": "Docs", "url": "https://example.com/docs"}],
            },
        ],
    }
    assert presentation_to_interactive_reply(presentation) == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [{"label": "Docs", "url": "https://example.com/docs"}],
            },
        ],
    }
    assert render_message_presentation_fallback_text({"presentation": presentation}) == (
        "- Docs: https://example.com/docs"
    )


def test_preserves_web_app_presentation_buttons() -> None:
    presentation = {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {"label": "Launch", "web_app": {"url": "https://example.com/app"}}
                ],
            },
        ],
    }
    normalized = normalize_message_presentation(presentation)
    assert normalized == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {"label": "Launch", "webApp": {"url": "https://example.com/app"}}
                ],
            },
        ],
    }
    assert presentation_to_interactive_reply(normalized) == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {"label": "Launch", "webApp": {"url": "https://example.com/app"}}
                ],
            },
        ],
    }
    assert render_message_presentation_fallback_text({"presentation": normalized}) == (
        "- Launch: https://example.com/app"
    )


def test_normalizes_typed_presentation_actions_and_bridges_to_legacy_values() -> None:
    normalized = normalize_message_presentation(
        {
            "blocks": [
                {
                    "type": "buttons",
                    "buttons": [
                        {
                            "label": "Plugins",
                            "action": {"type": "command", "command": "/codex plugins menu"},
                        },
                        {
                            "label": "Approve",
                            "action": {
                                "type": "callback",
                                "value": "/approve req allow-once",
                            },
                        },
                    ],
                },
            ],
        }
    )
    assert normalized == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Plugins",
                        "action": {"type": "command", "command": "/codex plugins menu"},
                    },
                    {
                        "label": "Approve",
                        "action": {
                            "type": "callback",
                            "value": "/approve req allow-once",
                        },
                    },
                ],
            },
        ],
    }
    assert presentation_to_interactive_reply(normalized) == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Plugins",
                        "action": {"type": "command", "command": "/codex plugins menu"},
                        "value": "/codex plugins menu",
                    },
                    {
                        "label": "Approve",
                        "action": {
                            "type": "callback",
                            "value": "/approve req allow-once",
                        },
                        "value": "/approve req allow-once",
                    },
                ],
            },
        ],
    }


def test_converts_only_presentation_controls_for_native_renderers() -> None:
    presentation = {
        "title": "Deploy approval",
        "blocks": [
            {"type": "text", "text": "Canary is ready."},
            {"type": "divider"},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Approve",
                        "value": "approve",
                        "style": "success",
                        "reusable": True,
                    },
                ],
            },
            {
                "type": "select",
                "placeholder": "Rollback target",
                "options": [{"label": "Previous", "value": "previous"}],
            },
        ],
    }
    assert presentation_to_interactive_reply(presentation) == {
        "blocks": [
            {"type": "text", "text": "Deploy approval"},
            {"type": "text", "text": "Canary is ready."},
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Approve",
                        "value": "approve",
                        "style": "success",
                        "reusable": True,
                    }
                ],
            },
            {
                "type": "select",
                "placeholder": "Rollback target",
                "options": [{"label": "Previous", "value": "previous"}],
            },
        ],
    }
    assert presentation_to_interactive_controls_reply(presentation) == {
        "blocks": [
            {
                "type": "buttons",
                "buttons": [
                    {
                        "label": "Approve",
                        "value": "approve",
                        "style": "success",
                        "reusable": True,
                    }
                ],
            },
            {
                "type": "select",
                "placeholder": "Rollback target",
                "options": [{"label": "Previous", "value": "previous"}],
            },
        ],
    }


def test_keeps_divider_only_fallback_empty_unless_send_transport_requests_it() -> None:
    presentation = {"blocks": [{"type": "divider"}]}
    assert render_message_presentation_fallback_text({"presentation": presentation}) == ""
    assert (
        render_message_presentation_fallback_text(
            {"presentation": presentation, "emptyFallback": "---"}
        )
        == "---"
    )


def test_has_message_presentation_blocks_and_interactive_variants() -> None:
    assert has_message_presentation_blocks(None) is False
    assert has_message_presentation_blocks({"blocks": []}) is False
    assert has_message_presentation_blocks(
        {"blocks": [{"type": "text", "text": "hi"}]}
    ) is True
    assert has_interactive_reply_blocks(None) is False
    assert has_interactive_reply_blocks({"blocks": []}) is False


def test_interactive_reply_to_presentation_roundtrip() -> None:
    interactive = {
        "blocks": [
            {"type": "text", "text": "Hello"},
            {
                "type": "buttons",
                "buttons": [{"label": "Retry", "value": "retry"}],
            },
            {
                "type": "select",
                "placeholder": "Pick",
                "options": [{"label": "A", "value": "a"}],
            },
        ]
    }
    presentation = normalize_message_presentation(
        interactive_reply_to_presentation(interactive)
    )
    assert presentation is not None
    assert presentation["blocks"][0] == {"type": "text", "text": "Hello"}


def test_resolve_interactive_text_fallback_uses_text_when_present() -> None:
    assert (
        resolve_interactive_text_fallback({"text": "override", "interactive": None})
        == "override"
    )


def test_render_fallback_text_handles_context_and_divider_blocks() -> None:
    presentation = {
        "blocks": [
            {"type": "context", "text": "Context note"},
            {"type": "divider"},
        ]
    }
    assert render_message_presentation_fallback_text({"presentation": presentation}) == (
        "Context note"
    )
