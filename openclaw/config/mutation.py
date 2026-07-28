from __future__ import annotations

import copy
from typing import Any, Callable

from openclaw.config.mutation_conflict import ConfigMutationConflictError
from openclaw.config.runtime_snapshot import (
    get_runtime_config_snapshot,
    get_runtime_config_source_snapshot,
    resolve_config_snapshot_hash,
    resolve_config_write_after_write,
    resolve_config_write_follow_up,
)
from openclaw.infra.errors import format_error_message


DEFAULT_CONFIG_MUTATION_RETRY_ATTEMPTS = 5


class ConfigMutationBase:
    RUNTIME = "runtime"
    SOURCE = "source"


class ConfigMutationIO:
    def __init__(self, **kwargs):
        self.env = kwargs.get("env")
        self.read_config_file_snapshot_for_write = kwargs.get(
            "readConfigFileSnapshotForWrite"
        )
        self.write_config_file = kwargs.get("writeConfigFile")


class ConfigMutationContext:
    def __init__(self, snapshot, previous_hash, attempt):
        self.snapshot = snapshot
        self.previous_hash = previous_hash
        self.attempt = attempt


class ConfigReplaceResult:
    def __init__(
        self,
        path: str,
        previous_hash: str | None,
        snapshot: dict[str, Any],
        next_config: dict[str, Any],
        persisted_hash: str | None,
        after_write: Any,
        follow_up: Any,
    ):
        self.path = path
        self.previous_hash = previous_hash
        self.snapshot = snapshot
        self.next_config = next_config
        self.persisted_hash = persisted_hash
        self.after_write = after_write
        self.follow_up = follow_up


class ConfigMutationResult(ConfigReplaceResult):
    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.result = kwargs.get("result")
        self.attempts = kwargs.get("attempts", 0)


async def replace_config_file(params: dict[str, Any]) -> ConfigReplaceResult:
    next_config = params.get("nextConfig", {})
    base_hash = params.get("baseHash")
    snapshot = params.get("snapshot")
    after_write = params.get("afterWrite")
    write_options = params.get("writeOptions", {})
    io = params.get("io")

    prepared = snapshot or {}
    merged_write_options = {**write_options, **(prepared.get("writeOptions", {}))}

    previous_hash = _assert_base_hash_matches(prepared, base_hash)
    resolved_after_write = resolve_config_write_after_write(
        after_write or write_options.get("afterWrite")
    )

    write_result = {
        "persistedHash": None,
        "persistedConfig": next_config,
    }

    return ConfigReplaceResult(
        path=prepared.get("path", ""),
        previous_hash=previous_hash,
        snapshot=prepared,
        next_config=write_result["persistedConfig"],
        persisted_hash=write_result["persistedHash"],
        after_write=resolved_after_write,
        follow_up=resolve_config_write_follow_up(resolved_after_write),
    )


async def transform_config_file(
    params: dict[str, Any],
) -> ConfigMutationResult:
    max_attempts = params.get("maxAttempts", 1)
    base = params.get("base", ConfigMutationBase.RUNTIME)
    base_hash = params.get("baseHash")
    after_write = params.get("afterWrite")
    write_options = params.get("writeOptions", {})
    io = params.get("io")
    commit = params.get("commit")
    transform_fn = params.get("transform")

    last_error = None
    for attempt in range(max_attempts):
        try:
            snapshot_data = {
                "path": "",
                "sourceConfig": {},
                "runtimeConfig": {},
                "parsed": {},
                "raw": None,
                "exists": False,
                "valid": True,
                "issues": [],
                "warnings": [],
                "legacyIssues": [],
            }
            snapshot = snapshot_data
            base_config = snapshot.get("runtimeConfig") if base == "runtime" else snapshot.get("sourceConfig")

            transformed = transform_fn(base_config, {
                "snapshot": snapshot,
                "previousHash": base_hash,
                "attempt": attempt,
            })

            next_config = transformed.get("nextConfig", {})
            result = transformed.get("result")

            committed = await replace_config_file({
                "nextConfig": next_config,
                "baseHash": base_hash,
                "snapshot": snapshot,
                "afterWrite": after_write,
                "writeOptions": write_options,
                "io": io,
            })

            return ConfigMutationResult(
                path=committed.path,
                previous_hash=committed.previous_hash,
                snapshot=committed.snapshot,
                next_config=committed.next_config,
                persisted_hash=committed.persisted_hash,
                after_write=committed.after_write,
                follow_up=committed.follow_up,
                result=result,
                attempts=attempt + 1,
            )
        except ConfigMutationConflictError as e:
            last_error = e
            if not e.retryable or attempt >= max_attempts - 1:
                raise
            continue
        except Exception as e:
            last_error = e
            raise

    raise last_error or Exception("Config mutation exhausted without success")


async def transform_config_file_with_retry(
    params: dict[str, Any],
) -> ConfigMutationResult:
    max_attempts = params.get("maxAttempts", DEFAULT_CONFIG_MUTATION_RETRY_ATTEMPTS)
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("Config mutation maxAttempts must be a positive integer.")
    return await transform_config_file({**params, "maxAttempts": max_attempts})


async def mutate_config_file(
    params: dict[str, Any],
) -> ConfigMutationResult:
    transform_fn = params.get("mutate")

    async def _transform(current_config, context):
        draft = copy.deepcopy(current_config) if isinstance(current_config, dict) else {}
        result = transform_fn(draft, context)
        if hasattr(result, "__await__"):
            result = await result
        return {"nextConfig": draft, "result": result}

    return await transform_config_file({**params, "transform": _transform})


async def mutate_config_file_with_retry(
    params: dict[str, Any],
) -> ConfigMutationResult:
    max_attempts = params.get("maxAttempts", DEFAULT_CONFIG_MUTATION_RETRY_ATTEMPTS)
    if not isinstance(max_attempts, int) or max_attempts < 1:
        raise ValueError("Config mutation maxAttempts must be a positive integer.")

    transform_fn = params.get("mutate")

    async def _transform(current_config, context):
        draft = copy.deepcopy(current_config) if isinstance(current_config, dict) else {}
        result = transform_fn(draft, context)
        if hasattr(result, "__await__"):
            result = await result
        return {"nextConfig": draft, "result": result}

    return await transform_config_file({
        **params,
        "maxAttempts": max_attempts,
        "transform": _transform,
    })


def _assert_base_hash_matches(snapshot: dict, expected_hash: str | None) -> str | None:
    current_hash = resolve_config_snapshot_hash(snapshot)
    if expected_hash is not None and expected_hash != current_hash:
        raise ConfigMutationConflictError(
            "config changed since last load",
            current_hash=current_hash,
        )
    return current_hash
