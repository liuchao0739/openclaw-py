"""Tests for commitments — config, store writer, model selection."""

from __future__ import annotations

from openclaw.commitments import (
    DEFAULT_COMMITMENT_EXPIRE_AFTER_HOURS,
    DEFAULT_COMMITMENT_MAX_PER_HEARTBEAT,
    resolve_commitment_default_model_ref,
    resolve_commitment_timezone,
    resolve_commitments_config,
    run_exclusive_commitments_store_write,
)


class TestResolveCommitmentsConfig:
    def test_defaults(self):
        config = resolve_commitments_config(None)
        assert config["enabled"] is False
        assert config["maxPerDay"] == 3
        assert config["extraction"]["debounceMs"] == 15_000
        assert config["extraction"]["confidenceThreshold"] == 0.72

    def test_enabled(self):
        config = resolve_commitments_config({"commitments": {"enabled": True}})
        assert config["enabled"] is True

    def test_custom_max_per_day(self):
        config = resolve_commitments_config({"commitments": {"maxPerDay": 10}})
        assert config["maxPerDay"] == 10

    def test_invalid_max_per_day(self):
        config = resolve_commitments_config({"commitments": {"maxPerDay": -5}})
        assert config["maxPerDay"] == 3  # fallback


class TestResolveCommitmentTimezone:
    def test_default(self):
        assert resolve_commitment_timezone(None) == "UTC"

    def test_from_config(self):
        cfg = {"agents": {"defaults": {"userTimezone": "America/New_York"}}}
        assert resolve_commitment_timezone(cfg) == "America/New_York"

    def test_empty_timezone(self):
        cfg = {"agents": {"defaults": {"userTimezone": "  "}}}
        assert resolve_commitment_timezone(cfg) == "UTC"


class TestResolveCommitmentDefaultModelRef:
    def test_fallback(self):
        result = resolve_commitment_default_model_ref(None)
        assert "provider" in result
        assert "model" in result

    def test_from_config(self):
        cfg = {"agents": {"defaults": {"model": "claude-4", "provider": "anthropic"}}}
        result = resolve_commitment_default_model_ref(cfg)
        assert result["model"] == "claude-4"
        assert result["provider"] == "anthropic"


class TestRunExclusiveCommitmentsStoreWrite:
    async def test_basic_write(self, tmp_path):
        store_path = str(tmp_path / "commitments.json")
        result = await run_exclusive_commitments_store_write(
            store_path,
            lambda: {"written": True},
        )
        assert result == {"written": True}

    async def test_async_fn(self, tmp_path):
        store_path = str(tmp_path / "commitments.json")

        async def write():
            return {"async": True}

        result = await run_exclusive_commitments_store_write(store_path, write)
        assert result == {"async": True}

    async def test_creates_parent_dir(self, tmp_path):
        store_path = str(tmp_path / "subdir" / "commitments.json")
        await run_exclusive_commitments_store_write(store_path, lambda: None)
        import os

        assert os.path.exists(os.path.dirname(store_path))


class TestConstants:
    def test_defaults(self):
        assert DEFAULT_COMMITMENT_MAX_PER_HEARTBEAT == 3
        assert DEFAULT_COMMITMENT_EXPIRE_AFTER_HOURS == 72
