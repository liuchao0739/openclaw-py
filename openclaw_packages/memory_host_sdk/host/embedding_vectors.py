from __future__ import annotations

from typing import List


def sanitize_and_normalize_embedding(vec: list) -> list:
    sanitized = [v if isinstance(v, (int, float)) and v == v else 0.0 for v in vec]
    magnitude = sum(v * v for v in sanitized) ** 0.5
    if magnitude < 1e-10:
        return sanitized
    return [v / magnitude for v in sanitized]


def normalize_embedding_vector(vec: List[float]) -> List[float]:
    return sanitize_and_normalize_embedding(vec)
