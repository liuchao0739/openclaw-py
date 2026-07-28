"""Shared env-var candidates append unique keys to owner-keyed buckets."""

from __future__ import annotations


def append_unique_env_var_candidates(
    target: dict[str, list[str]],
    owner_id: str,
    keys: list[str],
) -> None:
    normalized_owner_id = owner_id.strip()
    if not normalized_owner_id or len(keys) == 0:
        return
    bucket = target.setdefault(normalized_owner_id, [])
    seen = set(bucket)
    for key in keys:
        normalized_key = key.strip()
        if not normalized_key or normalized_key in seen:
            continue
        seen.add(normalized_key)
        bucket.append(normalized_key)
