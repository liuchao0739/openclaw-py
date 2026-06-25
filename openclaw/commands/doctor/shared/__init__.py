"""Commands/doctor/shared — object guards, allowlist predicates, config migration."""

from openclaw.commands.doctor.shared.allow_from_mode import (
    AllowFromMode,
    resolve_allow_from_mode,
)
from openclaw.commands.doctor.shared.allowlist import has_allow_from_entries
from openclaw.commands.doctor.shared.legacy_config_migrate import migrate_legacy_config
from openclaw.commands.doctor.shared.object import as_object_record

__all__ = [
    "AllowFromMode",
    "as_object_record",
    "has_allow_from_entries",
    "migrate_legacy_config",
    "resolve_allow_from_mode",
]
