from __future__ import annotations

import json
import os
import tempfile
from typing import Any, List, Optional

from .batch_http import post_json_with_retry
from .batch_output import apply_embedding_batch_output_line
from .batch_status import (
    resolve_batch_completion_from_status,
    resolve_completed_batch_result,
    throw_if_batch_terminal_failure,
)
from .batch_upload import upload_batch_jsonl_file
from .batch_utils import build_batch_headers, normalize_batch_base_url


def _resolve_safe_timeout_delay_ms(value: float, opts: Optional[dict] = None) -> float:
    min_ms = (opts or {}).get("minMs", 0)
    return max(value, min_ms)


def build_embedding_batch_group_options(
    max_batch_size: int = 100,
    max_concurrency: int = 2,
) -> dict:
    return {
        "maxBatchSize": max_batch_size,
        "maxConcurrency": max_concurrency,
    }


def run_embedding_batch_groups(
    chunks: list,
    provider: object,
    base_url: str,
    api_key: str,
    model: str,
    extra_headers: Optional[dict] = None,
    max_batch_size: int = 100,
    poll_interval_ms: float = 2000,
    timeout_ms: float = 600_000,
) -> list:
    if not chunks:
        return []

    groups = []
    for i in range(0, len(chunks), max_batch_size):
        groups.append(chunks[i:i + max_batch_size])

    all_results = []
    for group in groups:
        batch_entries = []
        custom_id_index_map = {}

        for idx, chunk in enumerate(group):
            custom_id = f"batch-{idx}"
            custom_id_index_map[custom_id] = idx
            text = chunk.get("text", "")
            batch_entries.append({
                "custom_id": custom_id,
                "model": model,
                "input": {
                    "text": text,
                    "type": "text-embedding",
                },
            })

        fd, batch_file_path = tempfile.mkstemp(suffix=".jsonl", prefix="embedding-batch-")
        try:
            with os.fdopen(fd, "w") as f:
                for entry in batch_entries:
                    f.write(json.dumps(entry) + "\n")

            result = upload_batch_jsonl_file(
                base_url=base_url,
                api_key=api_key,
                batch_file_path=batch_file_path,
                provider_id="remote",
                model=model,
                poll_interval_ms=poll_interval_ms,
                timeout_ms=timeout_ms,
                extra_headers=extra_headers,
            )

            throw_if_batch_terminal_failure(result)

            output = resolve_completed_batch_result(result)
            sorted_output = apply_embedding_batch_output_line(output, custom_id_index_map)
            all_results.extend(sorted_output)
        finally:
            try:
                os.unlink(batch_file_path)
            except OSError:
                pass

    return all_results


class BatchRunner:
    def __init__(self, cfg: dict, agent_id: str):
        self._cfg = cfg
        self._agent_id = agent_id

    def close(self) -> None:
        pass
