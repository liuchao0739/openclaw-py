"""ClickClack outbound target parsing helpers."""

from __future__ import annotations

import importlib

_RUNTIME_MODULE = "openclaw_extensions.clickclack.src.target_runtime"


def __getattr__(name: str) -> object:
    module = importlib.import_module(_RUNTIME_MODULE)
    return getattr(module, name)
