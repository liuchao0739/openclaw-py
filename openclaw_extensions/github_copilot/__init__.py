from .auth import resolveFirstGithubToken
from .embeddings import githubCopilotMemoryEmbeddingProviderAdapter
from .model_metadata import (
    COPILOT_CHAT_COMPLETIONS_COMPAT,
    COPILOT_XHIGH_MODEL_IDS,
    STATIC_MODEL_OVERRIDES,
    resolveCopilotTransportApi,
    resolveCopilotModelCompat,
    resolveCopilotExtendedThinkingLevels,
    resolveStaticCopilotModelOverride,
)
from .models import PROVIDER_ID, resolveCopilotForwardCompatModel, fetchCopilotModelCatalog
from .replay_policy import buildGithubCopilotReplayPolicy, sanitizeGithubCopilotReplayHistory
from .stream import wrapCopilotProviderStream
from .token import DEFAULT_COPILOT_API_BASE_URL, resolveCopilotApiToken, deriveCopilotApiBaseUrlFromToken
from .login import runGitHubCopilotDeviceFlow
from .index import load_github_copilot_extension

__all__ = [
    "resolveFirstGithubToken",
    "githubCopilotMemoryEmbeddingProviderAdapter",
    "COPILOT_CHAT_COMPLETIONS_COMPAT",
    "COPILOT_XHIGH_MODEL_IDS",
    "STATIC_MODEL_OVERRIDES",
    "resolveCopilotTransportApi",
    "resolveCopilotModelCompat",
    "resolveCopilotExtendedThinkingLevels",
    "resolveStaticCopilotModelOverride",
    "PROVIDER_ID",
    "resolveCopilotForwardCompatModel",
    "fetchCopilotModelCatalog",
    "buildGithubCopilotReplayPolicy",
    "sanitizeGithubCopilotReplayHistory",
    "wrapCopilotProviderStream",
    "DEFAULT_COPILOT_API_BASE_URL",
    "resolveCopilotApiToken",
    "deriveCopilotApiBaseUrlFromToken",
    "runGitHubCopilotDeviceFlow",
    "load_github_copilot_extension",
]