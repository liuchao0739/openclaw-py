from __future__ import annotations

import os
from typing import Any


class ProgressDisplay:
    def __init__(self, total: int = 0, label: str = ""):
        self.total = total
        self.current = 0
        self.label = label
        self._active = False

    def start(self) -> None:
        self._active = True
        self.current = 0
        self._render()

    def advance(self, step: int = 1) -> None:
        if not self._active:
            return
        self.current += step
        self._render()

    def complete(self) -> None:
        if not self._active:
            return
        self.current = self.total
        self._render(final=True)
        self._active = False
        print()

    def fail(self, message: str = "") -> None:
        if not self._active:
            return
        self._active = False
        if message:
            print(f"\n{message}")
        else:
            print()

    def _render(self, final: bool = False) -> None:
        if not sys_is_tty():
            return
        pct = int(self.current * 100 / self.total) if self.total > 0 else 0
        label = f"{self.label}: " if self.label else ""
        import sys

        sys.stdout.write(f"\r{label}{pct}% ({self.current}/{self.total})")
        sys.stdout.flush()


def sys_is_tty() -> bool:
    import sys

    return sys.stdout.isatty()
