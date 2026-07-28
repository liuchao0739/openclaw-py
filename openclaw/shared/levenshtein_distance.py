"""Levenshtein distance implementation for string comparison."""

from __future__ import annotations


def levenshtein_distance(left: str, right: str) -> int:
    if left == right:
        return 0
    if not left:
        return len(right)
    if not right:
        return len(left)
    previous = list(range(len(right) + 1))
    current = list(range(len(right) + 1))
    for left_index in range(len(left)):
        current[0] = left_index + 1
        for right_index in range(len(right)):
            cost = 0 if left[left_index] == right[right_index] else 1
            current[right_index + 1] = min(
                current[right_index] + 1,
                previous[right_index + 1] + 1,
                previous[right_index] + cost,
            )
        previous, current = current, previous
    return previous[len(right)]
