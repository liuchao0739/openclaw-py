"""System prompt type definitions — prompt rendering modes."""

from __future__ import annotations

from typing import Literal

PromptMode = Literal["full", "minimal", "none"]
SilentReplyPromptMode = Literal["generic", "none"]
