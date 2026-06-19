"""ACP runtime registry stub."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class AcpRuntimeBackend:
    id: str
    label: str


class AcpRuntimeRegistry:
    def __init__(self) -> None:
        self._backends: dict[str, AcpRuntimeBackend] = {}

    def register(self, backend: AcpRuntimeBackend) -> None:
        self._backends[backend.id] = backend

    def get(self, backend_id: str) -> AcpRuntimeBackend | None:
        return self._backends.get(backend_id)

    def list_backends(self) -> list[AcpRuntimeBackend]:
        return list(self._backends.values())


default_registry = AcpRuntimeRegistry()
