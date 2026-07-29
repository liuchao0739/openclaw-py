from typing import Any, Dict


def set_discord_runtime(runtime: Dict[str, Any]) -> None:
    from .runtime import set_discord_runtime as impl
    impl(runtime)
