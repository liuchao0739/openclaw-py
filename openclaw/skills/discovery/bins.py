"""Skill binary discovery helpers normalize executable metadata from skill manifests.

Mirrors src/skills/discovery/bins.ts.
"""

from __future__ import annotations

from typing import Any, Iterable, Mapping


def _normalize_optional_string(value: Any) -> str | None:
    if isinstance(value, str):
        s = value.strip()
        return s or None
    return None


def collect_skill_bins(entries: Iterable[Mapping[str, Any]]) -> list[str]:
    """Collect all binary names a set of skills may require or install."""
    bins: set[str] = set()
    for entry in entries:
        metadata = entry.get("metadata") or {}
        if not isinstance(metadata, Mapping):
            continue
        requires = metadata.get("requires") or {}
        if isinstance(requires, Mapping):
            required = requires.get("bins") or []
            any_bins = requires.get("anyBins") or []
            for bin_name in required if isinstance(required, list) else []:
                trimmed = bin_name.strip() if isinstance(bin_name, str) else ""
                if trimmed:
                    bins.add(trimmed)
            for bin_name in any_bins if isinstance(any_bins, list) else []:
                trimmed = bin_name.strip() if isinstance(bin_name, str) else ""
                if trimmed:
                    bins.add(trimmed)
        install = metadata.get("install") or []
        if isinstance(install, list):
            for spec in install:
                if isinstance(spec, Mapping):
                    spec_bins = spec.get("bins") or []
                    if isinstance(spec_bins, list):
                        for bin_name in spec_bins:
                            trimmed = _normalize_optional_string(bin_name)
                            if trimmed:
                                bins.add(trimmed)
    return sorted(bins)
