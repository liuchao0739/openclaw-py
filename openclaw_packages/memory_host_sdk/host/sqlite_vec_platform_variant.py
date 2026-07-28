from __future__ import annotations

import platform
from typing import Dict, Optional


def resolve_sqlite_vec_platform_variant() -> Optional[Dict[str, str]]:
    machine = platform.machine().lower()
    system = platform.system().lower()

    variants = {
        ("x86_64", "linux"): {"pkg": "sqlite-vec-linux-x64", "extensionPath": "sqlite-vec"},
        ("x86_64", "darwin"): {"pkg": "sqlite-vec-darwin-x64", "extensionPath": "sqlite-vec"},
        ("arm64", "linux"): {"pkg": "sqlite-vec-linux-arm64", "extensionPath": "sqlite-vec"},
        ("arm64", "darwin"): {"pkg": "sqlite-vec-darwin-arm64", "extensionPath": "sqlite-vec"},
    }

    return variants.get((machine, system))
