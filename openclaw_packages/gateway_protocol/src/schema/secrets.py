from typing import Literal, Final, Optional, List, Any

SECRET_KIND = Literal["env", "file", "value"]

SECRET_KIND_ENV: Literal["env"] = "env"
SECRET_KIND_FILE: Literal["file"] = "file"
SECRET_KIND_VALUE: Literal["value"] = "value"

SECRET_KINDS: Final[tuple] = (
    SECRET_KIND_ENV,
    SECRET_KIND_FILE,
    SECRET_KIND_VALUE,
)

class Secret:
    name: str
    kind: SECRET_KIND
    value: Optional[str]
    description: Optional[str]
    metadata: Optional[dict]

class SecretsListParams:
    metadata: Optional[dict]

class SecretsListResult:
    secrets: List[Secret]
    metadata: Optional[dict]

class SecretsGetParams:
    name: Optional[str]
    metadata: Optional[dict]

class SecretsGetResult:
    secrets: List[Secret]
    metadata: Optional[dict]

class SecretsCreateParams:
    secrets: List[Secret]
    metadata: Optional[dict]

class SecretsCreateResult:
    created: int
    metadata: Optional[dict]

class SecretsUpdateParams:
    secrets: List[Secret]
    metadata: Optional[dict]

class SecretsUpdateResult:
    updated: int
    metadata: Optional[dict]

class SecretsDeleteParams:
    names: List[str]
    metadata: Optional[dict]

class SecretsDeleteResult:
    deleted: int
    metadata: Optional[dict]
