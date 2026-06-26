"""Tests for process, vitest shims, and provider-runtime modules."""

from openclaw.plugins.capability_runtime_vitest_shims import (
    create_media_runtime_shim,
    create_config_runtime_shim,
    create_speech_core_shim,
)
from openclaw.provider_runtime import OperationRetryPolicy, DEFAULT_RETRY_POLICY


class TestVitestShims:
    def test_media_shim(self):
        result = create_media_runtime_shim()
        assert result["supported"] is False
        assert result["providers"] == []

    def test_config_shim(self):
        result = create_config_runtime_shim()
        assert result["loaded"] is False
        assert result["config"] == {}

    def test_speech_shim(self):
        result = create_speech_core_shim()
        assert result["available"] is False
        assert result["engines"] == []


class TestOperationRetryPolicy:
    def test_defaults(self):
        assert DEFAULT_RETRY_POLICY.max_retries == 3
        assert DEFAULT_RETRY_POLICY.base_delay_ms == 1000

    def test_compute_delay_exponential(self):
        policy = OperationRetryPolicy(jitter=False)
        assert policy.compute_delay(0) == 1000
        assert policy.compute_delay(1) == 2000
        assert policy.compute_delay(2) == 4000

    def test_compute_delay_capped(self):
        policy = OperationRetryPolicy(max_delay_ms=5000, jitter=False)
        assert policy.compute_delay(10) == 5000

    def test_should_retry(self):
        policy = OperationRetryPolicy(max_retries=3)
        assert policy.should_retry(0, Exception("x")) is True
        assert policy.should_retry(2, Exception("x")) is True
        assert policy.should_retry(3, Exception("x")) is False

    def test_custom_policy(self):
        policy = OperationRetryPolicy(max_retries=5, base_delay_ms=500)
        assert policy.max_retries == 5
        assert policy.base_delay_ms == 500
