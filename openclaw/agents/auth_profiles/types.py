"""Shared auth profile data contracts."""

from __future__ import annotations

from typing import Any, Literal, TypedDict, Union

OAuthProvider = str

AuthProfileFailureReason = Literal[
    "auth",
    "auth_permanent",
    "format",
    "overloaded",
    "rate_limit",
    "billing",
    "timeout",
    "model_not_found",
    "session_expired",
    "empty_response",
    "no_error_details",
    "unclassified",
    "unknown",
]

AuthProfileBlockedReason = Literal["subscription_limit"]
AuthProfileBlockedSource = Literal["codex_rate_limits", "wham"]


class SecretRef(TypedDict, total=False):
    source: str
    provider: str
    id: str


class LegacyOAuthRef(TypedDict, total=False):
    pass


class OAuthCredentials(TypedDict, total=False):
    access: str
    refresh: str
    expires: float
    provider: OAuthProvider
    email: str
    enterpriseUrl: str
    projectId: str
    accountId: str
    chatgptPlanType: str
    idToken: str


class ApiKeyCredential(TypedDict, total=False):
    type: Literal["api_key"]
    provider: str
    key: str
    keyRef: SecretRef
    copyToAgents: bool
    email: str
    displayName: str
    metadata: dict[str, str]


class TokenCredential(TypedDict, total=False):
    type: Literal["token"]
    provider: str
    token: str
    tokenRef: SecretRef
    copyToAgents: bool
    expires: float
    email: str
    displayName: str


class OAuthCredential(OAuthCredentials, total=False):
    type: Literal["oauth"]
    provider: str
    oauthRef: LegacyOAuthRef
    clientId: str
    copyToAgents: bool
    email: str
    displayName: str


AuthProfileCredential = Union[ApiKeyCredential, TokenCredential, OAuthCredential]


class ProfileUsageStats(TypedDict, total=False):
    lastUsed: float
    blockedUntil: float
    blockedReason: AuthProfileBlockedReason
    blockedSource: AuthProfileBlockedSource
    blockedModel: str
    cooldownUntil: float
    cooldownReason: AuthProfileFailureReason
    cooldownModel: str
    disabledUntil: float
    disabledReason: AuthProfileFailureReason
    errorCount: int
    failureCounts: dict[str, int]
    lastFailureAt: float


class AuthProfileState(TypedDict, total=False):
    order: dict[str, list[str]]
    lastGood: dict[str, str]
    usageStats: dict[str, ProfileUsageStats]


class AuthProfileSecretsStore(TypedDict):
    version: int
    profiles: dict[str, AuthProfileCredential]


class AuthProfileStateStore(TypedDict, total=False):
    version: int
    order: dict[str, list[str]]
    lastGood: dict[str, str]
    usageStats: dict[str, ProfileUsageStats]


class AuthProfileStore(AuthProfileState, total=False):
    version: int
    profiles: dict[str, AuthProfileCredential]
    runtimePersistedProfileIds: list[str]
    runtimeExternalProfileIds: list[str]
    runtimeExternalProfileIdsAuthoritative: bool