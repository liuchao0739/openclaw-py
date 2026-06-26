"""Defines plugin install security scan result types.

Mirrors src/plugins/install-security-scan.types.ts.
"""

from __future__ import annotations

from typing import Any, TypedDict


class InstallSafetyOverrides(TypedDict, total=False):
    config: dict[str, Any]
    dangerouslyForceUnsafeInstall: bool
    trustedSourceLinkedOfficialInstall: bool
