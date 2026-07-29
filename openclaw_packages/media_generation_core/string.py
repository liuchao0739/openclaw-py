from typing import Any, List, Optional, Sequence


def normalize_optional_string(value: Any) -> Optional[str]:
    if not isinstance(value, str):
        return None
    trimmed = value.strip()
    return trimmed if trimmed else None


def unique_trimmed_strings(values: Sequence[Any]) -> List[str]:
    seen = set()
    result: List[str] = []
    for value in values:
        normalized = normalize_optional_string(value)
        if not normalized or normalized in seen:
            continue
        seen.add(normalized)
        result.append(normalized)
    return result
