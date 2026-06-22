"""Provider-safe JSON Schema helpers for agent tools."""

from openclaw.agents.schema.clean_for_gemini import (
    GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS,
    clean_schema_for_gemini,
)
from openclaw.agents.schema.string_enum import optional_string_enum, string_enum
from openclaw.agents.schema.typebox import (
    CHANNEL_TARGET_DESCRIPTION,
    CHANNEL_TARGETS_DESCRIPTION,
    channel_target_schema,
    channel_targets_schema,
    optional_finite_number_schema,
    optional_non_negative_integer_schema,
    optional_positive_integer_schema,
)

__all__ = [
    "GEMINI_UNSUPPORTED_SCHEMA_KEYWORDS",
    "CHANNEL_TARGET_DESCRIPTION",
    "CHANNEL_TARGETS_DESCRIPTION",
    "channel_target_schema",
    "channel_targets_schema",
    "clean_schema_for_gemini",
    "optional_finite_number_schema",
    "optional_non_negative_integer_schema",
    "optional_positive_integer_schema",
    "optional_string_enum",
    "string_enum",
]