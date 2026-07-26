"""ClickClack HTTP client."""

from __future__ import annotations

import importlib

_RUNTIME_MODULE = "openclaw_extensions.clickclack.src.http_client_runtime"


def __getattr__(name: str) -> object:
    module = importlib.import_module(_RUNTIME_MODULE)
    return getattr(module, name)
