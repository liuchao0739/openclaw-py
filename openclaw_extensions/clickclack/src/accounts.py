"""Resolves ClickClack account configuration from root channel config."""

from __future__ import annotations

import importlib

_RUNTIME_MODULE = "openclaw_extensions.clickclack.src.accounts_runtime"


def __getattr__(name: str) -> object:
    module = importlib.import_module(_RUNTIME_MODULE)
    return getattr(module, name)
