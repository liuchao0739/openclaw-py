from __future__ import annotations

import json
from typing import Any


class HttpBody:
    def __init__(self, content: bytes | str | None = None):
        self._content = content

    @property
    def content(self) -> bytes:
        if self._content is None:
            return b""
        if isinstance(self._content, str):
            return self._content.encode("utf-8")
        return self._content

    @property
    def text(self) -> str:
        if self._content is None:
            return ""
        if isinstance(self._content, bytes):
            return self._content.decode("utf-8")
        return self._content

    @property
    def json(self) -> Any:
        return json.loads(self.text)

    @property
    def is_empty(self) -> bool:
        return len(self.content) == 0

    def __len__(self) -> int:
        return len(self.content)


class HttpErrorBody:
    @staticmethod
    def format(error: Exception) -> dict[str, Any]:
        return {
            "error": {
                "type": type(error).__name__,
                "message": str(error),
            }
        }

    @staticmethod
    def parse(body: HttpBody) -> dict[str, Any]:
        try:
            return body.json
        except (json.JSONDecodeError, ValueError):
            return {"error": {"type": "unknown", "message": body.text}}

    @staticmethod
    def extract_error_code(body: HttpBody) -> str | None:
        try:
            data = body.json
            if isinstance(data, dict) and "error" in data:
                error = data["error"]
                if isinstance(error, dict):
                    return error.get("code") or error.get("type")
                return str(error)
        except (json.JSONDecodeError, ValueError):
            pass
        return None
