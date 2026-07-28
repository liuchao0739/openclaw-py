from __future__ import annotations

from typing import List, Optional


def build_text_embedding_input(text: str) -> dict:
    return {"text": text}


def is_inline_data_embedding_input_part(part: dict) -> bool:
    return part.get("type") == "inline-data"


def has_non_text_embedding_parts(input_data: Optional[dict]) -> bool:
    if not input_data or not input_data.get("parts"):
        return False
    return any(is_inline_data_embedding_input_part(part) for part in input_data["parts"])
