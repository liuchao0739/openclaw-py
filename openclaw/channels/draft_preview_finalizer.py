"""Deprecated draft preview finalizer facade.

Mirrors src/channels/draft-preview-finalizer.ts.
"""

from __future__ import annotations

from typing import Any

DraftPreviewFinalizerDraft = Any
DraftPreviewFinalizerResult = Any

async def deliver_finalizable_draft_preview(*args: Any, **kwargs: Any) -> Any: ...
