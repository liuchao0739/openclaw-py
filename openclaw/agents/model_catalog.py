from __future__ import annotations

import json
import os
from typing import Any


def resolve_model_catalog_path() -> str:
    return os.path.join(".openclaw", "model-catalog.json")


def load_model_catalog() -> dict[str, Any]:
    path = resolve_model_catalog_path()
    if not os.path.exists(path):
        return {"providers": {}, "version": 1}
    try:
        with open(path, "r") as f:
            data = json.load(f)
        if isinstance(data, dict):
            return data
    except Exception:
        pass
    return {"providers": {}, "version": 1}


def save_model_catalog(catalog: dict[str, Any]) -> None:
    path = resolve_model_catalog_path()
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w") as f:
        json.dump(catalog, f, indent=2)
