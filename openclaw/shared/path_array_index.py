"""Path array index parser for config and JSON paths."""

from __future__ import annotations

import re

_MAX_CONFIG_PATH_ARRAY_INDEX = 100_000

_CANONICAL_ARRAY_INDEX_SEGMENT = re.compile(r"^(0|[1-9]\d*)$")


def parse_config_path_array_index(segment: str) -> int | None:
    if not _CANONICAL_ARRAY_INDEX_SEGMENT.match(segment):
        return None
    try:
        index = int(segment)
    except ValueError:
        return None
    if index > _MAX_CONFIG_PATH_ARRAY_INDEX:
        return None
    return index
