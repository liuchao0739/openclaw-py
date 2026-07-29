from typing import TypedDict, Optional, List, Any, Literal


FeishuDomain = str

FeishuChatType = Literal["p2p", "group", "topic_group", "private"]

FeishuGroupSessionScope = Literal["group", "group_sender", "group_topic", "group_topic_sender"]

FeishuIdType = Literal["open_id", "user_id", "union_id", "chat_id"]

FeishuDefaultAccountSelectionSource = Literal["explicit-default", "mapped-default", "fallback"]


class FeishuToolsConfig(TypedDict, total=False):
    doc: bool
    chat: bool
    wiki: bool
    drive: bool
    perm: bool
    scopes: bool
    bitable: bool
    base: bool


class FeishuAccountConfig(TypedDict, total=False):
    enabled: bool
    name: str
    appId: str
    appSecret: Any
    encryptKey: Any
    verificationToken: Any
    domain: FeishuDomain
    connectionMode: Literal["websocket", "webhook"]
    renderMode: Literal["auto", "raw", "card"]
    streaming: bool
    blockStreaming: bool
    replyInThread: Literal["disabled", "enabled"]
    typingIndicator: bool
    tools: FeishuToolsConfig


class FeishuConfig(TypedDict, total=False):
    enabled: bool
    defaultAccount: str
    appId: str
    appSecret: Any
    encryptKey: Any
    verificationToken: Any
    domain: FeishuDomain
    connectionMode: Literal["websocket", "webhook"]
    renderMode: Literal["auto", "raw", "card"]
    streaming: bool
    blockStreaming: bool
    replyInThread: Literal["disabled", "enabled"]
    typingIndicator: bool
    accounts: dict
    tools: FeishuToolsConfig
    httpTimeoutMs: int


class ResolvedFeishuAccount(TypedDict, total=False):
    accountId: str
    selectionSource: str
    enabled: bool
    configured: bool
    name: Optional[str]
    appId: Optional[str]
    appSecret: Optional[str]
    encryptKey: Optional[str]
    verificationToken: Optional[str]
    domain: FeishuDomain
    config: FeishuConfig


class FeishuMessageContext(TypedDict, total=False):
    chatId: str
    messageId: str
    replyTargetMessageId: Optional[str]
    typingTargetMessageId: Optional[str]
    suppressReplyTarget: bool
    senderId: str
    senderOpenId: str
    senderName: Optional[str]
    chatType: FeishuChatType
    mentionedBot: bool
    hasAnyMention: bool
    rootId: Optional[str]
    parentId: Optional[str]
    threadId: Optional[str]
    content: str
    contentType: str


class FeishuMessageInfo(TypedDict, total=False):
    messageId: str
    chatId: str
    chatType: Optional[FeishuChatType]
    senderId: Optional[str]
    senderOpenId: Optional[str]
    senderType: Optional[str]
    content: str
    contentType: str
    createTime: Optional[int]
    threadId: Optional[str]


class FeishuProbeResult(TypedDict, total=False):
    ok: bool
    appId: Optional[str]
    botName: Optional[str]
    botOpenId: Optional[str]


class FeishuSendResult(TypedDict, total=False):
    messageId: str
    chatId: str
    receipt: Any


class FeishuMediaInfo(TypedDict, total=False):
    path: str
    contentType: Optional[str]
    placeholder: str


class DynamicAgentCreationConfig(TypedDict, total=False):
    enabled: bool
    workspaceTemplate: str
    agentDirTemplate: str
    maxAgents: int


def is_feishu_group_chat_type(chat_type: Optional[str]) -> bool:
    return chat_type in ("group", "topic_group")
