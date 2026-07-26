"""Shared pytest fixtures."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

DEFAULT_TS_REPO = "/Users/liuchao/openclaw-ts"


def ts_repo_path() -> Path:
    return Path(os.environ.get("OPENCLAW_TS_REPO", DEFAULT_TS_REPO))


@pytest.fixture(scope="session")
def ts_repo() -> Path:
    """Checkout of the TypeScript source repo the port is derived from."""
    path = ts_repo_path()
    if not path.is_dir():
        pytest.skip(f"TypeScript source repo not available at {path}")
    return path
