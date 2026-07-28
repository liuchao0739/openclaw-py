from typing import Literal, Final, Optional, List, Any

from .primitives import InputProvenance

CHANNEL_KIND = Literal["group", "one-to-one"]

CHANNEL_KIND_GROUP: Literal["group"] = "group"
CHANNEL_KIND_ONE_TO_ONE: Literal["one-to-one"] = "one-to-one"

CHANNEL_KINDS: Final[tuple] = (
    CHANNEL_KIND_GROUP,
    CHANNEL_KIND_ONE_TO_ONE,
)

CHANNEL_ROLE = Literal["admin", "member", "owner", "read-only"]

CHANNEL_ROLE_ADMIN: Literal["admin"] = "admin"
CHANNEL_ROLE_MEMBER: Literal["member"] = "member"
CHANNEL_ROLE_OWNER: Literal["owner"] = "owner"
CHANNEL_ROLE_READ_ONLY: Literal["read-only"] = "read-only"

CHANNEL_ROLES: Final[tuple] = (
    CHANNEL_ROLE_ADMIN,
    CHANNEL_ROLE_MEMBER,
    CHANNEL_ROLE_OWNER,
    CHANNEL_ROLE_READ_ONLY,
)

class ChannelMember:
    member_id: str
    name: Optional[str]
    role: CHANNEL_ROLE
    metadata: Optional[dict]

class TalkGetParams:
    agent_id: Optional[str]
    channel_id: Optional[str]
    metadata: Optional[dict]

class TalkGetResult:
    channel_id: str
    channel_kind: CHANNEL_KIND
    channel_role: CHANNEL_ROLE
    members: List[ChannelMember]
    metadata: Optional[dict]

class TalkEnterParams:
    channel_id: str
    metadata: Optional[dict]

class TalkEnterResult:
    channel_id: str
    channel_kind: CHANNEL_KIND
    channel_role: CHANNEL_ROLE
    metadata: Optional[dict]

class TalkLeaveParams:
    channel_id: str
    metadata: Optional[dict]

class TalkLeaveResult:
    channel_id: str
    metadata: Optional[dict]

class TalkMessageParams:
    channel_id: str
    message: str
    provenance: Optional[InputProvenance]
    metadata: Optional[dict]

class TalkMessageResult:
    channel_id: str
    message_id: str
    metadata: Optional[dict]

class TalkTypingParams:
    channel_id: str
    is_typing: bool
    metadata: Optional[dict]

TalkGetRequest = Any
TalkEnterRequest = Any
TalkLeaveRequest = Any
TalkMessageRequest = Any
TalkTypingRequest = Any
TalkGetResponse = Any
TalkEnterResponse = Any
TalkLeaveResponse = Any
TalkMessageResponse = Any
