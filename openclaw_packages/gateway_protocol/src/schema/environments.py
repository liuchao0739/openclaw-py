from typing import Optional, List, Any

class Environment:
    name: str
    value: Optional[str]
    description: Optional[str]
    metadata: Optional[dict]

class EnvironmentsGetParams:
    metadata: Optional[dict]

class EnvironmentsGetResult:
    environments: List[Environment]
    metadata: Optional[dict]

class EnvironmentsUpdateParams:
    environments: List[Environment]
    metadata: Optional[dict]

class EnvironmentsUpdateResult:
    updated: int
    metadata: Optional[dict]

class EnvironmentsPatchParams:
    patch: Any
    metadata: Optional[dict]

class EnvironmentsPatchResult:
    patched: int
    metadata: Optional[dict]

class EnvironmentsDeleteParams:
    names: List[str]
    metadata: Optional[dict]

class EnvironmentsDeleteResult:
    deleted: int
    metadata: Optional[dict]

class EnvironmentsCreateParams:
    environments: List[Environment]
    metadata: Optional[dict]

class EnvironmentsCreateResult:
    created: int
    metadata: Optional[dict]

class EnvironmentsListParams:
    metadata: Optional[dict]

class EnvironmentsListResult:
    environments: List[Environment]
    metadata: Optional[dict]
