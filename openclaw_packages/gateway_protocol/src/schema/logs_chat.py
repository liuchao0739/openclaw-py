from typing import Literal, Final, Optional, List, Any

LOG_LEVEL = Literal["debug", "info", "warn", "error"]

LOG_LEVEL_DEBUG: Literal["debug"] = "debug"
LOG_LEVEL_INFO: Literal["info"] = "info"
LOG_LEVEL_WARN: Literal["warn"] = "warn"
LOG_LEVEL_ERROR: Literal["error"] = "error"

LOG_LEVELS: Final[tuple] = (
    LOG_LEVEL_DEBUG,
    LOG_LEVEL_INFO,
    LOG_LEVEL_WARN,
    LOG_LEVEL_ERROR,
)

class LogEntry:
    level: LOG_LEVEL
    message: str
    timestamp: Optional[str]
    metadata: Optional[dict]

class LogsChatGetParams:
    session_key: Optional[str]
    metadata: Optional[dict]

class LogsChatGetResult:
    logs: List[LogEntry]
    metadata: Optional[dict]

class LogsChatAppendParams:
    session_key: str
    entry: LogEntry
    metadata: Optional[dict]

class LogsChatAppendResult:
    session_key: str
    metadata: Optional[dict]

class LogsChatRotateParams:
    session_key: str
    metadata: Optional[dict]

class LogsChatRotateResult:
    session_key: str
    metadata: Optional[dict]
