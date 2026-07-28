from __future__ import annotations

from typing import Any, Dict, List, Optional


def resolve_memory_cache_summary() -> Dict[str, Any]:
    return {
        "type": "cache-summary",
        "totalEntries": 0,
        "hitRate": 0.0,
        "missRate": 0.0,
    }


def resolve_memory_fts_state() -> Dict[str, Any]:
    return {
        "type": "fts-state",
        "enabled": False,
        "indexedDocuments": 0,
    }


def resolve_memory_vector_state() -> Dict[str, Any]:
    return {
        "type": "vector-state",
        "enabled": False,
        "dimensions": 0,
        "model": "",
    }


class Tone:
    NEUTRAL = "neutral"
    POSITIVE = "positive"
    NEGATIVE = "negative"
    HOSTILE = "hostile"


def resolve_tone_summary() -> Dict[str, Any]:
    return {
        "type": "tone-summary",
        "tones": [Tone.NEUTRAL],
        "confidence": 0.0,
    }
