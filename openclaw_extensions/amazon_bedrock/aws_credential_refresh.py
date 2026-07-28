from __future__ import annotations

import os
from typing import Any


def _has_static_aws_credential_env(env: dict[str, str]) -> bool:
    return bool(env.get("AWS_ACCESS_KEY_ID") and env.get("AWS_SECRET_ACCESS_KEY"))


def should_refresh_aws_shared_config_cache_for_bedrock(
    env: dict[str, str] | None = None,
) -> bool:
    if env is None:
        env = os.environ
    if env.get("AWS_BEDROCK_SKIP_AUTH") == "1" or env.get("AWS_BEARER_TOKEN_BEDROCK"):
        return False
    return not _has_static_aws_credential_env(env)


async def refresh_aws_shared_config_cache_for_bedrock(
    env: dict[str, str] | None = None,
) -> None:
    if not should_refresh_aws_shared_config_cache_for_bedrock(env):
        return
    try:
        from smithy_bedrock_runtime.config import load_shared_config_files
        await load_shared_config_files(ignore_cache=True)
    except ImportError:
        pass


__all__ = [
    "refresh_aws_shared_config_cache_for_bedrock",
    "should_refresh_aws_shared_config_cache_for_bedrock",
]