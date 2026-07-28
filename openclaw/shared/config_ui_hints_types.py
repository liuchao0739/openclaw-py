"""UI metadata attached to config schema paths for forms, docs, and redaction policy."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class ConfigUiHint:
    label: str | None = None
    help: str | None = None
    tags: list[str] | None = None
    group: str | None = None
    order: int | None = None
    advanced: bool | None = None
    sensitive: bool | None = None
    placeholder: str | None = None
    item_template: Any = None


ConfigUiHints = dict[str, ConfigUiHint]
