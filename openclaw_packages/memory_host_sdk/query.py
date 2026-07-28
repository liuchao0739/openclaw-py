from __future__ import annotations

from typing import Any, Dict, List, Optional

from .host.config_utils import normalize_agent_id
from .host.query_expansion import expand_query, extract_keywords
from .host.types import MemorySearchResult


def expand_search_query(query: str, cfg: dict, agent_id: str) -> Dict[str, Any]:
    keywords = extract_keywords(query)
    expanded = expand_query(query)
    return {
        "original": query,
        "keywords": keywords,
        "expanded": expanded,
    }


def extract_query_keywords(query: str) -> List[str]:
    return extract_keywords(query)
