from typing import Optional, Any

class ConfigGetParams:
    path: Optional[str]
    metadata: Optional[dict]

class ConfigGetResult:
    config: Any
    metadata: Optional[dict]

class ConfigUpdateParams:
    config: Any
    metadata: Optional[dict]

class ConfigUpdateResult:
    config: Any
    metadata: Optional[dict]

class ConfigPatchParams:
    patch: Any
    metadata: Optional[dict]

class ConfigPatchResult:
    config: Any
    metadata: Optional[dict]
