from typing import Literal, Final, Optional, List, Any

PLUGIN_TYPE = Literal["extension", "middleware", "tool"]

PLUGIN_TYPE_EXTENSION: Literal["extension"] = "extension"
PLUGIN_TYPE_MIDDLEWARE: Literal["middleware"] = "middleware"
PLUGIN_TYPE_TOOL: Literal["tool"] = "tool"

PLUGIN_TYPES: Final[tuple] = (
    PLUGIN_TYPE_EXTENSION,
    PLUGIN_TYPE_MIDDLEWARE,
    PLUGIN_TYPE_TOOL,
)

class Plugin:
    plugin_id: str
    name: str
    version: Optional[str]
    plugin_type: PLUGIN_TYPE
    enabled: bool
    metadata: Optional[dict]

class PluginsListParams:
    metadata: Optional[dict]

class PluginsListResult:
    plugins: List[Plugin]
    metadata: Optional[dict]

class PluginsInstallParams:
    name: str
    version: Optional[str]
    metadata: Optional[dict]

class PluginsInstallResult:
    plugin_id: str
    name: str
    version: Optional[str]
    metadata: Optional[dict]

class PluginsUninstallParams:
    plugin_id: str
    metadata: Optional[dict]

class PluginsUninstallResult:
    plugin_id: str
    metadata: Optional[dict]

class PluginsUpdateParams:
    plugin_id: str
    version: Optional[str]
    metadata: Optional[dict]

class PluginsUpdateResult:
    plugin_id: str
    version: Optional[str]
    metadata: Optional[dict]

class PluginsEnableParams:
    plugin_id: str
    metadata: Optional[dict]

class PluginsEnableResult:
    plugin_id: str
    metadata: Optional[dict]

class PluginsDisableParams:
    plugin_id: str
    metadata: Optional[dict]

class PluginsDisableResult:
    plugin_id: str
    metadata: Optional[dict]

class PluginsConfigGetParams:
    plugin_id: str
    metadata: Optional[dict]

class PluginsConfigGetResult:
    config: Any
    metadata: Optional[dict]

class PluginsConfigPatchParams:
    plugin_id: str
    patch: Any
    metadata: Optional[dict]

class PluginsConfigPatchResult:
    config: Any
    metadata: Optional[dict]
