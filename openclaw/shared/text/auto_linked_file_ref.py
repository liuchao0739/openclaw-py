from __future__ import annotations

import re

from openclaw_packages.normalization_core import normalize_lowercase_string_or_empty

_FILE_REF_EXTENSIONS = ("md", "go", "py", "pl", "sh", "am", "at", "be", "cc")

FILE_REF_EXTENSIONS_WITH_TLD = frozenset(_FILE_REF_EXTENSIONS)


def is_auto_linked_file_ref(href: str, label: str) -> bool:
    stripped = re.sub(r"^https?://", "", href, count=1, flags=re.IGNORECASE)
    if stripped != label:
        return False
    dot_index = label.rfind(".")
    if dot_index < 1:
        return False
    ext = normalize_lowercase_string_or_empty(label[dot_index + 1:])
    if ext not in FILE_REF_EXTENSIONS_WITH_TLD:
        return False
    segments = label.split("/")
    if len(segments) > 1:
        for segment in segments[:-1]:
            if "." in segment:
                return False
    return True
