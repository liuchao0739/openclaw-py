"""Tests for interactive payload helpers."""

from openclaw.interactive import (
    normalize_button_style,
    normalize_presentation_tone,
    normalize_button_label,
    normalize_button_action,
    normalize_button,
    normalize_buttons,
)


class TestNormalizeButtonStyle:
    def test_valid(self):
        assert normalize_button_style("primary") == "primary"
        assert normalize_button_style("DANGER") == "danger"

    def test_invalid(self):
        assert normalize_button_style("purple") is None
        assert normalize_button_style(None) is None


class TestNormalizePresentationTone:
    def test_valid(self):
        assert normalize_presentation_tone("info") == "info"
        assert normalize_presentation_tone("WARNING") == "warning"

    def test_invalid(self):
        assert normalize_presentation_tone("blue") is None


class TestNormalizeButtonLabel:
    def test_valid(self):
        assert normalize_button_label("Click me") == "Click me"

    def test_empty(self):
        assert normalize_button_label("") is None
        assert normalize_button_label("  ") is None

    def test_non_string(self):
        assert normalize_button_label(42) is None


class TestNormalizeButtonAction:
    def test_command(self):
        action = normalize_button_action({"type": "command", "command": "/help"})
        assert action == {"type": "command", "command": "/help"}

    def test_callback(self):
        action = normalize_button_action({"type": "callback", "value": "abc123"})
        assert action == {"type": "callback", "value": "abc123"}

    def test_invalid(self):
        assert normalize_button_action(None) is None
        assert normalize_button_action({"type": "unknown"}) is None
        assert normalize_button_action({"type": "command"}) is None


class TestNormalizeButton:
    def test_valid(self):
        btn = normalize_button({"label": "OK", "style": "primary"})
        assert btn["label"] == "OK"
        assert btn["style"] == "primary"

    def test_no_label(self):
        assert normalize_button({"style": "primary"}) is None

    def test_with_action(self):
        btn = normalize_button({
            "label": "Run",
            "action": {"type": "command", "command": "/run"},
        })
        assert btn["action"]["command"] == "/run"

    def test_with_url(self):
        btn = normalize_button({"label": "Link", "url": "https://example.com"})
        assert btn["url"] == "https://example.com"

    def test_with_priority(self):
        btn = normalize_button({"label": "X", "priority": 5})
        assert btn["priority"] == 5

    def test_with_disabled(self):
        btn = normalize_button({"label": "X", "disabled": True})
        assert btn["disabled"] is True


class TestNormalizeButtons:
    def test_list(self):
        buttons = normalize_buttons([
            {"label": "A"},
            {"label": "B", "style": "danger"},
            {"no_label": True},
        ])
        assert len(buttons) == 2
        assert buttons[0]["label"] == "A"

    def test_empty(self):
        assert normalize_buttons([]) == []

    def test_non_list(self):
        assert normalize_buttons("not a list") is None or normalize_buttons("not a list") == []
