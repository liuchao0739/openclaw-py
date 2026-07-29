"""Gateway managed image attachment store.

Mirrors src/gateway/managed-image-attachments.ts.
"""

from __future__ import annotations

from typing import Any

DEFAULT_MANAGED_IMAGE_ATTACHMENT_LIMITS: Any = None

ManagedImageAttachmentLimits = Any

def resolve_managed_image_attachment_limits(*args: Any, **kwargs: Any) -> Any: ...
async def cleanup_managed_outgoing_image_records(*args: Any, **kwargs: Any) -> Any: ...
async def attach_managed_outgoing_images_to_message(*args: Any, **kwargs: Any) -> Any: ...
async def create_managed_outgoing_image_blocks(*args: Any, **kwargs: Any) -> Any: ...
async def handle_managed_outgoing_image_http_request(*args: Any, **kwargs: Any) -> Any: ...
