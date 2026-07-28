from __future__ import annotations

import json
import os
from typing import Any


class KeyedAsyncQueue:
    def __init__(self):
        self._queues: dict[str, list[Any]] = {}
        self._processing: set[str] = set()

    async def enqueue(self, key: str, item: Any) -> None:
        if key not in self._queues:
            self._queues[key] = []
        self._queues[key].append(item)

    async def process(self, key: str, handler: Any) -> list[Any]:
        if key in self._processing:
            return []
        self._processing.add(key)

        results = []
        queue = self._queues.get(key, [])
        self._queues[key] = []

        for item in queue:
            try:
                result = await handler(item)
                results.append(result)
            except Exception as e:
                results.append({"error": str(e)})

        self._processing.discard(key)
        return results

    def pending(self, key: str) -> int:
        return len(self._queues.get(key, []))

    def has_key(self, key: str) -> bool:
        return key in self._queues and len(self._queues[key]) > 0


class AsyncJsonlQueue:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self._items: list[dict[str, Any]] = []

    async def enqueue(self, item: dict[str, Any]) -> None:
        self._items.append(item)
        await self._flush()

    async def _flush(self) -> None:
        if not self._items:
            return
        os.makedirs(os.path.dirname(self.file_path), exist_ok=True)
        with open(self.file_path, "a", encoding="utf-8") as f:
            for item in self._items:
                f.write(json.dumps(item, ensure_ascii=False) + "\n")
        self._items.clear()

    def read_all(self) -> list[dict[str, Any]]:
        results = []
        try:
            with open(self.file_path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        results.append(json.loads(line))
                    except json.JSONDecodeError:
                        pass
        except FileNotFoundError:
            pass
        return results

    def clear(self) -> None:
        try:
            os.remove(self.file_path)
        except FileNotFoundError:
            pass
