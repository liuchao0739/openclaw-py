"""Tests for auto_reply/usage_bar — contract, translator, template."""

from __future__ import annotations

from openclaw.auto_reply.usage_bar import (
    DEFAULT_USAGE_BAR_TEMPLATE,
    build_usage_contract,
    render_usage_bar,
    render_usage_bar_line,
    translate_usage_contract,
)


class TestBuildUsageContract:
    def test_empty_state(self):
        contract = build_usage_contract({})
        assert contract["schema"] == "openclaw.usageLine.v1"
        assert contract["model"]["id"] is None
        assert contract["usage"]["has_tokens"] is False

    def test_with_model(self):
        state = {"model": "gpt-4", "provider": "openai"}
        contract = build_usage_contract(state)
        assert contract["model"]["id"] == "gpt-4"
        assert contract["model"]["provider"] == "openai"

    def test_with_usage(self):
        state = {"usage": {"input": 100, "output": 50, "cacheRead": 200}}
        contract = build_usage_contract(state)
        assert contract["usage"]["input_tokens"] == 100
        assert contract["usage"]["output_tokens"] == 50
        assert contract["usage"]["cache_read_tokens"] == 200
        assert contract["usage"]["has_tokens"] is True
        assert contract["usage"]["has_split_tokens"] is True
        assert contract["usage"]["cache_hit_pct"] is not None

    def test_total_only(self):
        state = {"usage": {"total": 500}}
        contract = build_usage_contract(state)
        assert contract["usage"]["has_total_only_tokens"] is True
        assert contract["usage"]["has_split_tokens"] is False

    def test_context_pct(self):
        state = {"contextTokenBudget": 10000, "contextUsedTokens": 5000}
        contract = build_usage_contract(state)
        assert contract["context"]["pct_used"] == 50

    def test_with_surface(self):
        contract = build_usage_contract({}, surface="telegram")
        assert contract["surface"] == "telegram"

    def test_override(self):
        state = {"overrideSource": "user"}
        contract = build_usage_contract(state)
        assert contract["model"]["is_override"] is True

    def test_override_auto(self):
        state = {"overrideSource": "auto"}
        contract = build_usage_contract(state)
        assert contract["model"]["is_override"] is False

    def test_cost(self):
        state = {"turnUsd": 0.0042}
        contract = build_usage_contract(state)
        assert contract["cost"]["available"] is True
        assert contract["cost"]["turn_usd"] == 0.0042

    def test_identity(self):
        state = {"identity": {"name": "Agent", "emoji": "🤖"}}
        contract = build_usage_contract(state)
        assert contract["identity"]["name"] == "Agent"
        assert contract["identity"]["emoji"] == "🤖"


class TestTranslateUsageContract:
    def test_empty_contract(self):
        text = translate_usage_contract({})
        assert text == ""

    def test_model_only(self):
        contract = {"model": {"id": "gpt-4", "display_name": "gpt-4"}}
        text = translate_usage_contract(contract)
        assert "gpt-4" in text

    def test_with_usage(self):
        contract = {
            "model": {"id": "gpt-4"},
            "usage": {
                "has_tokens": True,
                "input_tokens": 100,
                "output_tokens": 50,
            },
        }
        text = translate_usage_contract(contract)
        assert "in:" in text
        assert "out:" in text

    def test_with_context(self):
        contract = {"context": {"pct_used": 75}}
        text = translate_usage_contract(contract)
        assert "ctx:75%" in text

    def test_format_num(self):
        from openclaw.auto_reply.usage_bar.translator import _format_num

        assert _format_num(500) == "500"
        assert _format_num(1500) == "1.5K"
        assert _format_num(1_500_000) == "1.5M"

    def test_format_duration(self):
        from openclaw.auto_reply.usage_bar.translator import _format_duration

        assert _format_duration(500) == "500ms"
        assert _format_duration(1500) == "1.5s"
        assert _format_duration(90_000) == "1.5min"


class TestRenderUsageBar:
    def test_render(self):
        contract = {"model": {"id": "gpt-4"}, "usage": {"has_tokens": True, "input_tokens": 100}}
        text = render_usage_bar(contract)
        assert "gpt-4" in text

    def test_render_line(self):
        contract = {"model": {"id": "gpt-4"}}
        text = render_usage_bar_line(contract)
        assert text.startswith("📊")

    def test_render_empty(self):
        assert render_usage_bar({}) == ""
        assert render_usage_bar_line({}) == ""


class TestDefaultTemplate:
    def test_schema(self):
        assert DEFAULT_USAGE_BAR_TEMPLATE["schema"] == "openclaw.usageBar.v1"

    def test_defaults(self):
        assert DEFAULT_USAGE_BAR_TEMPLATE["showModel"] is True
        assert DEFAULT_USAGE_BAR_TEMPLATE["showUsage"] is True
