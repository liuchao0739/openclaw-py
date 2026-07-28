from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any


def read_json_file(file_path: str) -> dict[str, Any]:
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def write_json_file(file_path: str, data: dict[str, Any], *, indent: int = 2) -> None:
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=indent, ensure_ascii=False)
        f.write("\n")


def read_json_file_if_exists(file_path: str) -> dict[str, Any] | None:
    try:
        return read_json_file(file_path)
    except (FileNotFoundError, json.JSONDecodeError):
        return None


class JsonFile:
    def __init__(self, file_path: str):
        self.file_path = file_path

    def read(self) -> dict[str, Any]:
        return read_json_file(self.file_path)

    def write(self, data: dict[str, Any]) -> None:
        write_json_file(self.file_path, data)

    def exists(self) -> bool:
        return os.path.exists(self.file_path)

    def delete(self) -> None:
        try:
            os.remove(self.file_path)
        except FileNotFoundError:
            pass
