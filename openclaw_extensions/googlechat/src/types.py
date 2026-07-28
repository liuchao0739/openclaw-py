from __future__ import annotations

from typing import Any, Literal, TypedDict


class GoogleChatSpace(TypedDict, total=False):
    name: str
    displayName: str
    type: str
    spaceType: str
    singleUserBotDm: bool


class GoogleChatUser(TypedDict, total=False):
    name: str
    displayName: str
    email: str
    type: str


class GoogleChatThread(TypedDict, total=False):
    name: str
    threadKey: str


class GoogleChatAttachmentDataRef(TypedDict, total=False):
    resourceName: str
    attachmentUploadToken: str


class GoogleChatAttachment(TypedDict, total=False):
    name: str
    contentName: str
    contentType: str
    thumbnailUri: str
    downloadUri: str
    source: str
    attachmentDataRef: GoogleChatAttachmentDataRef
    driveDataRef: dict[str, Any]


class GoogleChatUserMention(TypedDict, total=False):
    user: GoogleChatUser
    type: str


class GoogleChatAnnotation(TypedDict, total=False):
    type: str
    startIndex: int
    length: int
    userMention: GoogleChatUserMention
    slashCommand: dict[str, Any]
    richLinkMetadata: dict[str, Any]
    customEmojiMetadata: dict[str, Any]


class GoogleChatActionParameter(TypedDict, total=False):
    key: str
    value: str


class GoogleChatAction(TypedDict, total=False):
    actionMethodName: str
    parameters: list[GoogleChatActionParameter]


class GoogleChatEvent(TypedDict, total=False):
    type: str
    eventType: str
    eventTime: str
    space: GoogleChatSpace
    user: GoogleChatUser
    message: GoogleChatMessage
    action: GoogleChatAction
    common: dict[str, Any]
    commonEventObject: dict[str, Any]


class GoogleChatReaction(TypedDict, total=False):
    name: str
    user: GoogleChatUser
    emoji: dict[str, str]


class GoogleChatTextParagraphWidget(TypedDict):
    textParagraph: dict[str, str]


class GoogleChatButtonWidget(TypedDict):
    buttonList: dict[str, Any]


class GoogleChatDividerWidget(TypedDict):
    divider: dict[str, Any]


GoogleChatWidget = GoogleChatTextParagraphWidget | GoogleChatButtonWidget | GoogleChatDividerWidget


class GoogleChatCardV2(TypedDict, total=False):
    cardId: str
    card: dict[str, Any]


class GoogleChatMessage(TypedDict, total=False):
    name: str
    text: str
    argumentText: str
    sender: GoogleChatUser
    thread: GoogleChatThread
    cardsV2: list[GoogleChatCardV2]
    attachment: list[GoogleChatAttachment]
    annotations: list[GoogleChatAnnotation]