from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class SecretInput(BaseModel):
    source: Literal["env", "file", "inline", "ref"] | None = None
    key: str | None = None
    value: str | None = None
    ref: str | None = None

    model_config = {"extra": "allow"}


class SecretsConfig(BaseModel):
    providers: dict[str, Any] | None = None
    defaults: dict[str, Any] | None = None
    resolution: dict[str, Any] | None = None

    model_config = {"extra": "allow"}
