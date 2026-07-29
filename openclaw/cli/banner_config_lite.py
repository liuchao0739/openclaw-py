from __future__ import annotations

from typing import Any

TaglineMode = str


def parse_tagline_mode(value: Any) -> str | None:
    if value in ("random", "default", "off"):
        return value
    return None


def read_cli_banner_tagline_mode(env: dict | None = None) -> str | None:
    import os

    env_map = env if env is not None else dict(os.environ)
    try:
        from openclaw.config.loader import load_config

        parsed = load_config()
        cli = getattr(parsed, "cli", None) if parsed else None
        if cli:
            banner = getattr(cli, "banner", None)
            if banner:
                return parse_tagline_mode(getattr(banner, "taglineMode", None))
    except Exception:
        pass
    return None
