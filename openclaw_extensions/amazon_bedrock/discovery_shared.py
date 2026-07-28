from __future__ import annotations

import os
from typing import Any

from openclaw.plugin_sdk.provider_auth_runtime import resolve_aws_sdk_env_var_name


def resolve_bedrock_config_api_key(
    env: dict[str, str] | None = None,
) -> str | None:
    if env is None:
        env = os.environ
    return resolve_aws_sdk_env_var_name(env)


def merge_implicit_bedrock_provider(params: dict[str, Any]) -> dict[str, Any]:
    existing = params.get("existing")
    implicit = params.get("implicit")
    if existing is None:
        return implicit
    models = existing.get("models")
    if isinstance(models, list) and len(models) > 0:
        final_models = models
    else:
        final_models = implicit.get("models")
    return {
        **implicit,
        **existing,
        "models": final_models,
    }


__all__ = [
    "merge_implicit_bedrock_provider",
    "resolve_bedrock_config_api_key",
]