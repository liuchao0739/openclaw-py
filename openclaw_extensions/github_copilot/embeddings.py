from typing import Dict, List, Optional

from .auth import resolveFirstGithubToken
from .token import DEFAULT_COPILOT_API_BASE_URL, resolveCopilotApiToken

COPILOT_EMBEDDING_PROVIDER_ID = "github-copilot"

PREFERRED_MODELS = ["text-embedding-3-small", "text-embedding-3-large", "text-embedding-ada-002"]

COPILOT_HEADERS_STATIC = {
    "Content-Type": "application/json",
}
COPILOT_ERROR_BODY_LIMIT_BYTES = 8 * 1024
COPILOT_EMBEDDINGS_RESPONSE_MAX_BYTES = 64 * 1024 * 1024


def isCopilotSetupError(err: Exception) -> bool:
    message = str(err)
    return any(phrase in message for phrase in [
        "No GitHub token available",
        "Copilot token exchange failed",
        "Copilot token response",
        "No embedding models available",
        "GitHub Copilot model discovery",
        "github-copilot.model-discovery",
        "GitHub Copilot embedding model",
        "Unexpected response from GitHub Copilot token endpoint",
    ])


async def discoverEmbeddingModels(params: Dict) -> List[str]:
    import requests

    baseUrl = params.get("baseUrl")
    copilotToken = params.get("copilotToken")
    headers = params.get("headers") or {}

    url = f"{baseUrl.rstrip('/')}/models"
    response = requests.get(url, headers={
        **COPILOT_HEADERS_STATIC,
        **headers,
        "Authorization": f"Bearer {copilotToken}",
    })

    if not response.ok:
        detail = response.text[:COPILOT_ERROR_BODY_LIMIT_BYTES]
        raise ValueError(f"GitHub Copilot model discovery HTTP {response.status}: {detail}")

    payload = response.json()
    allModels = payload.get("data", []) if isinstance(payload.get("data"), list) else []

    embeddingModels = []
    for entry in allModels:
        entry_id = str(entry.get("id", "")).strip() if isinstance(entry.get("id"), str) else ""
        if not entry_id:
            continue
        endpoints = entry.get("supported_endpoints", [])
        hasEmbeddingEndpoint = any(isinstance(e, str) and "embeddings" in e for e in endpoints)
        isEmbeddingModel = hasEmbeddingEndpoint or "embedding" in entry_id.lower()
        if isEmbeddingModel:
            embeddingModels.append(entry_id)
    return embeddingModels


def pickBestModel(available: List[str], userModel: Optional[str] = None) -> str:
    if userModel:
        normalized = userModel.strip()
        stripped = normalized[len(f"{COPILOT_EMBEDDING_PROVIDER_ID}/"):] if normalized.startswith(f"{COPILOT_EMBEDDING_PROVIDER_ID}/") else normalized
        if not available:
            raise ValueError("No embedding models available from GitHub Copilot")
        if stripped not in available:
            raise ValueError(f"GitHub Copilot embedding model \"{stripped}\" is not available. Available: {', '.join(available)}")
        return stripped

    for preferred in PREFERRED_MODELS:
        if preferred in available:
            return preferred
    if available:
        return available[0]
    raise ValueError("No embedding models available from GitHub Copilot")


def parseGitHubCopilotEmbeddingPayload(payload: Dict, expectedCount: int) -> List[List[float]]:
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("GitHub Copilot embeddings response missing data[]")

    vectors = [None] * expectedCount
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("GitHub Copilot embeddings response contains an invalid entry")
        indexValue = entry.get("index")
        embedding = entry.get("embedding")
        index = int(indexValue) if isinstance(indexValue, int) else float("nan")
        if not isinstance(index, int) or index < 0 or index >= expectedCount:
            raise ValueError("GitHub Copilot embeddings response contains an invalid index")
        if vectors[index] is not None:
            raise ValueError("GitHub Copilot embeddings response contains duplicate indexes")
        if not isinstance(embedding, list) or not all(isinstance(v, (int, float)) for v in embedding):
            raise ValueError("GitHub Copilot embeddings response contains an invalid embedding")
        vectors[index] = [float(v) for v in embedding]

    for i in range(expectedCount):
        if vectors[i] is None:
            raise ValueError("GitHub Copilot embeddings response missing vectors for some inputs")
    return vectors


async def resolveGitHubCopilotEmbeddingSession(client: Dict) -> Dict:
    token = await resolveCopilotApiToken({
        "githubToken": client.get("githubToken"),
        "env": client.get("env"),
    })
    baseUrl = client.get("baseUrl", "").strip() or token.get("baseUrl") or DEFAULT_COPILOT_API_BASE_URL
    return {
        "baseUrl": baseUrl,
        "headers": {
            **COPILOT_HEADERS_STATIC,
            **(client.get("headers") or {}),
            "Authorization": f"Bearer {token.get('token')}",
        },
    }


async def createGitHubCopilotEmbeddingProvider(client: Dict) -> Dict:
    import requests

    initialSession = await resolveGitHubCopilotEmbeddingSession(client)

    async def embed(inputTexts: List[str], signal=None):
        if not inputTexts:
            return []

        session = await resolveGitHubCopilotEmbeddingSession(client)
        url = f"{session['baseUrl'].rstrip('/')}/embeddings"

        response = requests.post(url, headers=session["headers"], json={"model": client["model"], "input": inputTexts})
        if not response.ok:
            detail = response.text[:COPILOT_ERROR_BODY_LIMIT_BYTES]
            raise ValueError(f"GitHub Copilot embeddings HTTP {response.status}: {detail}")

        payload = response.json()
        return parseGitHubCopilotEmbeddingPayload(payload, len(inputTexts))

    async def embed_query(text, options=None):
        if not text:
            return []
        results = await embed([text])
        return results[0] if results else []

    async def embed_batch(texts, options=None):
        return await embed(texts)

    return {
        "provider": {
            "id": COPILOT_EMBEDDING_PROVIDER_ID,
            "model": client["model"],
            "embedQuery": embed_query,
            "embedBatch": embed_batch,
        },
        "client": {
            **client,
            "baseUrl": initialSession["baseUrl"],
        },
    }


async def create_copilot_embedding_provider(options):
    remoteGithubToken = options.get("remote", {}).get("apiKey") or ""
    result = await resolveFirstGithubToken({
        "agentDir": options.get("agentDir"),
        "config": options.get("config"),
        "env": {},
    })
    profileGithubToken = result.get("githubToken", "")
    githubToken = remoteGithubToken or profileGithubToken

    if not githubToken:
        raise ValueError("No GitHub token available for Copilot embedding provider")

    tokenResult = await resolveCopilotApiToken({"githubToken": githubToken, "env": {}})
    copilotToken = tokenResult.get("token")
    resolvedBaseUrl = tokenResult.get("baseUrl")
    baseUrl = options.get("remote", {}).get("baseUrl", "").strip() or resolvedBaseUrl or DEFAULT_COPILOT_API_BASE_URL

    availableModels = await discoverEmbeddingModels({
        "baseUrl": baseUrl,
        "copilotToken": copilotToken,
        "headers": options.get("remote", {}).get("headers"),
    })

    userModel = options.get("model", "").strip() or None
    model = pickBestModel(availableModels, userModel)

    providerResult = await createGitHubCopilotEmbeddingProvider({
        "baseUrl": baseUrl,
        "env": {},
        "githubToken": githubToken,
        "headers": options.get("remote", {}).get("headers"),
        "model": model,
    })

    return {
        "provider": providerResult["provider"],
        "runtime": {
            "id": COPILOT_EMBEDDING_PROVIDER_ID,
            "cacheKeyData": {
                "provider": COPILOT_EMBEDDING_PROVIDER_ID,
                "baseUrl": baseUrl,
                "model": model,
            },
        },
    }


githubCopilotMemoryEmbeddingProviderAdapter = {
    "id": COPILOT_EMBEDDING_PROVIDER_ID,
    "transport": "remote",
    "authProviderId": COPILOT_EMBEDDING_PROVIDER_ID,
    "autoSelectPriority": 15,
    "allowExplicitWhenConfiguredAuto": True,
    "shouldContinueAutoSelection": isCopilotSetupError,
    "create": create_copilot_embedding_provider,
}

__all__ = ["githubCopilotMemoryEmbeddingProviderAdapter"]