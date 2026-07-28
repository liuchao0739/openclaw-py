from __future__ import annotations

import warnings
from typing import Any, Dict, Optional


def install_process_warning_filter() -> None:
    warnings.filterwarnings("ignore")


def should_ignore_warning(warning: object) -> bool:
    return False
