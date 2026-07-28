import re
from typing import Final

SINGLE_VALUE_FILE_REF_ID: Final[str] = "value"

SECRET_PROVIDER_ALIAS_PATTERN: Final[re.Pattern] = re.compile(r"^[a-z][a-z0-9_-]{0,63}$")

EXEC_SECRET_REF_ID_JSON_SCHEMA_PATTERN: Final[str] = r"^[a-zA-Z0-9_./-]+$"

FILE_SECRET_REF_ID_ABSOLUTE_JSON_SCHEMA_PATTERN: Final[str] = r"^/(?:[a-zA-Z0-9_.-]+/)*[a-zA-Z0-9_.-]+$"

FILE_SECRET_REF_ID_INVALID_ESCAPE_JSON_SCHEMA_PATTERN: Final[str] = r"\\[^ntrbfavx\d]"
