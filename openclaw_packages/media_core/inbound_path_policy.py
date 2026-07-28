from __future__ import annotations

import posixpath
import re

WILDCARD_SEGMENT = "*"
WINDOWS_DRIVE_ABS_RE = re.compile(r"^[A-Za-z]:/")
WINDOWS_DRIVE_ROOT_RE = re.compile(r"^[A-Za-z]:$")


def _normalize_posix_absolute_path(value: str) -> str | None:
    trimmed = value.strip()
    if not trimmed or "\0" in trimmed:
        return None
    normalized = posixpath.normpath(trimmed.replace("\\", "/"))
    is_absolute = normalized.startswith("/") or bool(WINDOWS_DRIVE_ABS_RE.match(normalized))
    if not is_absolute or normalized == "/":
        return None
    without_trailing_slash = normalized[:-1] if normalized.endswith("/") else normalized
    if bool(WINDOWS_DRIVE_ROOT_RE.match(without_trailing_slash)):
        return None
    return without_trailing_slash


def _split_path_segments(value: str) -> list[str]:
    return [seg for seg in value.split("/") if seg]


def _matches_root_pattern(candidate_path: str, root_pattern: str) -> bool:
    candidate_segments = _split_path_segments(candidate_path)
    root_segments = _split_path_segments(root_pattern)
    if len(candidate_segments) < len(root_segments):
        return False
    for idx, expected in enumerate(root_segments):
        actual = candidate_segments[idx]
        if expected == WILDCARD_SEGMENT:
            continue
        if expected != actual:
            return False
    return True


def is_valid_inbound_path_root_pattern(value: str) -> bool:
    normalized = _normalize_posix_absolute_path(value)
    if not normalized:
        return False
    segments = _split_path_segments(normalized)
    if not segments:
        return False
    return all(segment == WILDCARD_SEGMENT or "*" not in segment for segment in segments)


def normalize_inbound_path_roots(roots: list[str] | tuple[str, ...] | None = None) -> list[str]:
    normalized: list[str] = []
    seen: set[str] = set()
    for root in roots or []:
        if not isinstance(root, str):
            continue
        if not is_valid_inbound_path_root_pattern(root):
            continue
        candidate = _normalize_posix_absolute_path(root)
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        normalized.append(candidate)
    return normalized


def merge_inbound_path_roots(*roots_lists: list[str] | tuple[str, ...] | None) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for roots in roots_lists:
        normalized = normalize_inbound_path_roots(roots)
        for root in normalized:
            if root in seen:
                continue
            seen.add(root)
            merged.append(root)
    return merged


def is_inbound_path_allowed(file_path: str, roots: list[str] | tuple[str, ...], fallback_roots: list[str] | tuple[str, ...] | None = None) -> bool:
    candidate_path = _normalize_posix_absolute_path(file_path)
    if not candidate_path:
        return False
    normalized_roots = normalize_inbound_path_roots(roots)
    effective_roots = normalized_roots if normalized_roots else normalize_inbound_path_roots(fallback_roots)
    if not effective_roots:
        return False
    return any(_matches_root_pattern(candidate_path, root_pattern) for root_pattern in effective_roots)
