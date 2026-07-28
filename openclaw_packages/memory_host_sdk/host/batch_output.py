from __future__ import annotations

from typing import Any, Dict, List, Optional


def apply_embedding_batch_output_line(
    output: list,
    custom_id_index_map: dict,
) -> list:
    result = []
    for entry in output:
        custom_id = entry.get("custom_id", "")
        index = custom_id_index_map.get(custom_id)
        if index is not None:
            result.append((index, entry))
    result.sort(key=lambda x: x[0])
    return [entry for _, entry in result]
