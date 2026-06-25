"""Session diagnostics types.

Tracks resource loading issues and warnings for display in the UI.
"""

from __future__ import annotations

from typing import Literal, TypedDict

DiagnosticType = Literal["warning", "error", "info"]


class ResourceDiagnostic(TypedDict, total=False):
    type: DiagnosticType
    message: str
    path: str


def create_diagnostic(
    diag_type: DiagnosticType,
    message: str,
    path: str = "",
) -> ResourceDiagnostic:
    """Create a resource diagnostic entry."""
    return ResourceDiagnostic(type=diag_type, message=message, path=path)


def is_warning(diagnostic: ResourceDiagnostic) -> bool:
    return diagnostic.get("type") == "warning"


def is_error(diagnostic: ResourceDiagnostic) -> bool:
    return diagnostic.get("type") == "error"


def is_info(diagnostic: ResourceDiagnostic) -> bool:
    return diagnostic.get("type") == "info"
