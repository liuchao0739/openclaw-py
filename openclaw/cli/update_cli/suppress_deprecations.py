"""Suppress deprecation warnings.

Python equivalent of Node.js process.noDeprecation / NODE_NO_WARNINGS.
"""

from __future__ import annotations

import os
import warnings


def suppress_deprecations() -> None:
    """Suppress deprecation warnings for the current process."""
    os.environ["NODE_NO_WARNINGS"] = "1"
    warnings.filterwarnings("ignore", category=DeprecationWarning)
    warnings.filterwarnings("ignore", category=PendingDeprecationWarning)
