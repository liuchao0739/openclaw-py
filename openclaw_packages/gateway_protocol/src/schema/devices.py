from typing import Literal, Final, Optional, List, Any

DEVICES_TRUST_LEVEL = Literal["trusted", "untrusted"]

DEVICES_TRUST_LEVEL_TRUSTED: Literal["trusted"] = "trusted"
DEVICES_TRUST_LEVEL_UNTRUSTED: Literal["untrusted"] = "untrusted"

DEVICES_TRUST_LEVELS: Final[tuple] = (
    DEVICES_TRUST_LEVEL_TRUSTED,
    DEVICES_TRUST_LEVEL_UNTRUSTED,
)

class Device:
    device_id: str
    name: Optional[str]
    trust_level: DEVICES_TRUST_LEVEL
    metadata: Optional[dict]

class DevicesPairParams:
    device_id: str
    metadata: Optional[dict]

class DevicesPairResult:
    device_id: str
    metadata: Optional[dict]

class DevicesTrustParams:
    device_id: str
    trust_level: DEVICES_TRUST_LEVEL
    metadata: Optional[dict]

class DevicesTrustResult:
    device_id: str
    trust_level: DEVICES_TRUST_LEVEL
    metadata: Optional[dict]

class DevicesListParams:
    metadata: Optional[dict]

class DevicesListResult:
    devices: List[Device]
    metadata: Optional[dict]

class DevicesRevokeParams:
    device_id: str
    metadata: Optional[dict]

class DevicesRevokeResult:
    device_id: str
    metadata: Optional[dict]
