from __future__ import annotations

import os


def has_clawhub_risk_acknowledgement(env: dict | None = None) -> bool:
    env_map = env if env is not None else dict(os.environ)
    return env_map.get("OPENCLAW_CLAWHUB_RISK_ACKNOWLEDGED") == "1"


def require_clawhub_risk_acknowledgement(env: dict | None = None) -> None:
    if not has_clawhub_risk_acknowledgement(env):
        raise RuntimeError("ClawHub risk not acknowledged. Set OPENCLAW_CLAWHUB_RISK_ACKNOWLEDGED=1.")
