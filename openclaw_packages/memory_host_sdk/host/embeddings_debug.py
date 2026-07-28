from __future__ import annotations

import logging
from typing import Optional

_logger = logging.getLogger("memory")


def debug_embeddings_log(message: str, *args: object) -> None:
    _logger.debug(message, *args)
