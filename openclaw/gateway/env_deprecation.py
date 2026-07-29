"""Gateway legacy environment warning.

Mirrors src/gateway/env-deprecation.ts.
"""

from __future__ import annotations

from typing import Any

def warn_legacy_open_claw_env_vars(*args: Any, **kwargs: Any) -> Any: ...
def reset_legacy_open_claw_env_warning_for_test(*args: Any, **kwargs: Any) -> Any: ...
