from __future__ import annotations

import threading


def wait_forever() -> None:
    event = threading.Event()
    event.wait()
