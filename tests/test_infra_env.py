"""Tests for openclaw.infra.env."""

from __future__ import annotations

import os
from collections.abc import Iterator
from contextlib import contextmanager

import pytest

from openclaw.infra import env as env_module
from openclaw.infra.env import (
    is_pytest_runtime_env,
    is_truthy_env_value,
    log_accepted_env_option,
    normalize_env,
    normalize_zai_env,
)


@contextmanager
def with_env(overrides: dict[str, str | None]) -> Iterator[dict[str, str]]:
    backup = dict(os.environ)
    try:
        for key, value in overrides.items():
            if value is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = value
        yield os.environ
    finally:
        os.environ.clear()
        os.environ.update(backup)


@pytest.fixture(autouse=True)
def clear_logged_env() -> Iterator[None]:
    env_module._logged_env.clear()
    yield
    env_module._logged_env.clear()


def test_normalize_zai_env_copies_legacy() -> None:
    with with_env({"ZAI_API_KEY": "", "Z_AI_API_KEY": "zai-legacy"}):
        normalize_zai_env()
        assert os.environ["ZAI_API_KEY"] == "zai-legacy"


def test_normalize_zai_env_keeps_existing() -> None:
    with with_env({"ZAI_API_KEY": "zai-current", "Z_AI_API_KEY": "zai-legacy"}):
        normalize_zai_env()
        assert os.environ["ZAI_API_KEY"] == "zai-current"


def test_normalize_zai_env_ignores_blank_legacy() -> None:
    with with_env({"ZAI_API_KEY": "", "Z_AI_API_KEY": "   "}):
        normalize_zai_env()
        assert os.environ["ZAI_API_KEY"] == ""


def test_is_truthy_env_value() -> None:
    assert is_truthy_env_value("1") is True
    assert is_truthy_env_value("true") is True
    assert is_truthy_env_value(" yes ") is True
    assert is_truthy_env_value("ON") is True
    assert is_truthy_env_value("0") is False
    assert is_truthy_env_value("false") is False
    assert is_truthy_env_value("") is False
    assert is_truthy_env_value(None) is False


def test_normalize_env() -> None:
    with with_env({"ZAI_API_KEY": "", "Z_AI_API_KEY": "zai-legacy"}):
        normalize_env()
        assert os.environ["ZAI_API_KEY"] == "zai-legacy"


def test_log_accepted_env_option_skips_pytest(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PYTEST_CURRENT_TEST", "tests/test_infra_env.py::test")
    log_accepted_env_option(key="OPENCLAW_TEST_ENV", description="test", value="secret")


def test_is_pytest_runtime_env() -> None:
    assert is_pytest_runtime_env({"PYTEST_CURRENT_TEST": "x"}) is True
    assert is_pytest_runtime_env({"NODE_ENV": "test"}) is True
    assert is_pytest_runtime_env({}) is False
