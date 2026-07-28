from __future__ import annotations

from typing import Any


class DiagnosticTraceContext:
    def __init__(self, name: str, **metadata):
        self.name = name
        self.metadata = metadata
        self._spans: list[dict[str, Any]] = []
        self._current_span: dict[str, Any] | None = None

    def start_span(self, name: str, **kwargs) -> dict[str, Any]:
        span = {
            "name": name,
            "metadata": kwargs,
            "status": "active",
        }
        self._current_span = span
        self._spans.append(span)
        return span

    def end_span(self, status: str = "ok", **results) -> None:
        if self._current_span:
            self._current_span["status"] = status
            self._current_span["results"] = results
            self._current_span = None

    def get_spans(self) -> list[dict[str, Any]]:
        return list(self._spans)

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        if self._current_span:
            status = "error" if exc_type else "ok"
            self.end_span(status)


class DiagnosticSpan:
    def __init__(self, name: str, **metadata):
        self.name = name
        self.metadata = metadata
        self.status = "active"
        self.results: dict[str, Any] = {}

    def end(self, status: str = "ok", **results) -> None:
        self.status = status
        self.results = results
