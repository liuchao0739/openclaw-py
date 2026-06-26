"""Tests for skills/discovery modules."""

from openclaw.skills.discovery.bins import collect_skill_bins
from openclaw.skills.discovery.filter import (
    normalize_skill_filter,
    normalize_skill_filter_for_comparison,
    matches_skill_filter,
)


class TestCollectSkillBins:
    def test_required_bins(self):
        entries = [{"metadata": {"requires": {"bins": ["python", "node"]}}}]
        assert collect_skill_bins(entries) == ["node", "python"]

    def test_any_bins(self):
        entries = [{"metadata": {"requires": {"anyBins": ["ffmpeg"]}}}]
        assert collect_skill_bins(entries) == ["ffmpeg"]

    def test_install_bins(self):
        entries = [{"metadata": {"install": [{"bins": ["rustc", "cargo"]}]}}]
        assert collect_skill_bins(entries) == ["cargo", "rustc"]

    def test_dedup_and_sort(self):
        entries = [
            {"metadata": {"requires": {"bins": ["python", "node"]}}},
            {"metadata": {"requires": {"bins": ["python", "git"]}}},
        ]
        result = collect_skill_bins(entries)
        assert result == ["git", "node", "python"]

    def test_empty(self):
        assert collect_skill_bins([]) == []

    def test_no_metadata(self):
        assert collect_skill_bins([{}]) == []

    def test_trims_whitespace(self):
        entries = [{"metadata": {"requires": {"bins": ["  python  "]}}}]
        assert collect_skill_bins(entries) == ["python"]


class TestNormalizeSkillFilter:
    def test_none(self):
        assert normalize_skill_filter(None) is None

    def test_strings(self):
        assert normalize_skill_filter(["a", "b"]) == ["a", "b"]

    def test_filters_non_strings(self):
        assert normalize_skill_filter(["a", 1, "b"]) == ["a", "b"]

    def test_trims(self):
        assert normalize_skill_filter(["  a  ", "b"]) == ["a", "b"]

    def test_empty_list(self):
        assert normalize_skill_filter([]) == []


class TestNormalizeSkillFilterForComparison:
    def test_none(self):
        assert normalize_skill_filter_for_comparison(None) is None

    def test_sorted_unique(self):
        result = normalize_skill_filter_for_comparison(["b", "a", "b"])
        assert result == ["a", "b"]


class TestMatchesSkillFilter:
    def test_both_none(self):
        assert matches_skill_filter(None, None) is True

    def test_one_none(self):
        assert matches_skill_filter(None, ["a"]) is False
        assert matches_skill_filter(["a"], None) is False

    def test_same(self):
        assert matches_skill_filter(["a", "b"], ["b", "a"]) is True

    def test_different(self):
        assert matches_skill_filter(["a"], ["b"]) is False

    def test_different_length(self):
        assert matches_skill_filter(["a", "b"], ["a"]) is False

    def test_empty_both(self):
        assert matches_skill_filter([], []) is True
