from __future__ import annotations

from typing import Any, Literal, Optional, Dict

from pydantic import BaseModel, Field


class SecretInput(BaseModel):
    source: Optional[Literal["env", "file", "inline", "ref"]] = None
    key: Optional[str] = None
    value: Optional[str] = None
    ref: Optional[str] = None

    model_config = {"extra": "allow"}


class SecretsConfig(BaseModel):
    providers: Optional[Dict[str, Any]] = None
    defaults: Optional[Dict[str, Any]] = None
    resolution: Optional[Dict[str, Any]] = None

    model_config = {"extra": "allow"}
