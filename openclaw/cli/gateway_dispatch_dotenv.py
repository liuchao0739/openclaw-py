from __future__ import annotations

from typing import Any

from openclaw.cli.dotenv import load_dotenv


def dispatch_gateway_dotenv(env_file: str | None = None) -> dict[str, str]:
    return load_dotenv(env_file)
