from __future__ import annotations

from typing import Any, TypedDict

from openclaw.packages.normalization_core import normalize_optional_lowercase_string


class BooleanParseOptions(TypedDict, total=False):
    truthy: list[str]
    falsy: list[str]


DEFAULT_TRUTHY = ["true", "1", "yes", "on"]
DEFAULT_FALSY = ["false", "0", "no", "off"]
DEFAULT_TRUTHY_SET = set(DEFAULT_TRUTHY)
DEFAULT_FALSY_SET = set(DEFAULT_FALSY)


def as_boolean(value: Any) -> bool | None:
    return value if isinstance(value, bool) else None


def parse_boolean_value(value: Any, options: BooleanParseOptions | None = None) -> bool | None:
    boolean_value = as_boolean(value)
    if boolean_value is not None:
        return boolean_value
    if not isinstance(value, str):
        return None
    normalized = normalize_optional_lowercase_string(value)
    if not normalized:
        return None
    opts = options or {}
    truthy = opts.get("truthy", DEFAULT_TRUTHY)
    falsy = opts.get("falsy", DEFAULT_FALSY)
    truthy_set = DEFAULT_TRUTHY_SET if truthy == DEFAULT_TRUTHY else set(truthy)
    falsy_set = DEFAULT_FALSY_SET if falsy == DEFAULT_FALSY else set(falsy)
    if normalized in truthy_set:
        return True
    if normalized in falsy_set:
        return False
    return None
