"""Commands/models — alias, errors, local-url, set-image."""

from openclaw.commands.models.alias_name import normalize_alias
from openclaw.commands.models.list_errors import (
    MODEL_AVAILABILITY_UNAVAILABLE_CODE,
    format_error_with_stack,
    should_fallback_to_auth_heuristics,
)
from openclaw.commands.models.list_local_url import is_local_base_url
from openclaw.commands.models.set_image import models_set_image_command

__all__ = [
    "MODEL_AVAILABILITY_UNAVAILABLE_CODE",
    "format_error_with_stack",
    "is_local_base_url",
    "models_set_image_command",
    "normalize_alias",
    "should_fallback_to_auth_heuristics",
]
