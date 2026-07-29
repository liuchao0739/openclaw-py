"""Gateway operator scope constants.

Mirrors src/gateway/operator-scopes.ts.
"""

from __future__ import annotations

from typing import Any

ADMIN_SCOPE: Any = None
READ_SCOPE: Any = None
WRITE_SCOPE: Any = None
APPROVALS_SCOPE: Any = None
PAIRING_SCOPE: Any = None
TALK_SECRETS_SCOPE: Any = None

OperatorScope = Any

def is_operator_scope(*args: Any, **kwargs: Any) -> Any: ...
