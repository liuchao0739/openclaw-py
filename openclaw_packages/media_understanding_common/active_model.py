"""Active media-understanding model selection contract."""

from __future__ import annotations

from typing import TypedDict


class ActiveMediaModel(TypedDict, total=False):
    provider: str
    model: str
