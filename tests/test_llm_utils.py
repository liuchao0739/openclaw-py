"""Tests for LLM utils modules."""

from openclaw.llm.utils.headers import headers_to_record
from openclaw.llm.utils.hash import short_hash
from openclaw.llm.utils.sanitize_unicode import sanitize_surrogates


class TestHeadersToRecord:
    def test_dict(self):
        result = headers_to_record({"Content-Type": "application/json"})
        assert result == {"Content-Type": "application/json"}

    def test_none(self):
        assert headers_to_record(None) == {}

    def test_items_method(self):
        class H:
            def items(self):
                return [("Accept", "text/html")]
        result = headers_to_record(H())
        assert result == {"Accept": "text/html"}


class TestShortHash:
    def test_deterministic(self):
        assert short_hash("hello") == short_hash("hello")

    def test_different_inputs(self):
        assert short_hash("hello") != short_hash("world")

    def test_empty_string(self):
        h = short_hash("")
        assert isinstance(h, str)
        assert len(h) > 0

    def test_long_string(self):
        h = short_hash("x" * 1000)
        assert isinstance(h, str)

    def test_returns_hex(self):
        h = short_hash("test")
        assert all(c in "0123456789abcdef" for c in h)


class TestSanitizeSurrogates:
    def test_normal_text_unchanged(self):
        assert sanitize_surrogates("hello world") == "hello world"

    def test_emoji_preserved(self):
        text = "Hello 🙈 World"
        assert sanitize_surrogates(text) == text

    def test_unpaired_high_surrogate_removed(self):
        # U+D83D is a high surrogate without a matching low surrogate
        text = "Text " + chr(0xD83D) + " here"
        result = sanitize_surrogates(text)
        assert chr(0xD83D) not in result
        assert "Text" in result
        assert "here" in result

    def test_unpaired_low_surrogate_removed(self):
        # U+DC00 is a low surrogate without a matching high surrogate
        text = "Text " + chr(0xDC00) + " here"
        result = sanitize_surrogates(text)
        assert chr(0xDC00) not in result

    def test_empty_string(self):
        assert sanitize_surrogates("") == ""

    def test_non_string(self):
        assert sanitize_surrogates(123) == ""
