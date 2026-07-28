from __future__ import annotations

import json
import os
from typing import Any

from openclaw.plugin_sdk.provider_auth import build_copilot_ide_headers
from openclaw.plugin_sdk.secret_input_runtime import resolve_configured_secret_input_string

from openclaw_extensions.github_copilot.auth import resolve_first_github_token
from openclaw_extensions.github_copilot.token import (
    DEFAULT_COPILOT_API_BASE_URL,
    resolve_copilot_api_token,
)

COPILOT_EMBEDDING_PROVIDER_ID = "github-copilot"

PREFERRED_MODELS = [
    "text-embedding-3-small",
    "text-embedding-3-large",
    "text-embedding-ada-002",
]

COPILOT_HEADERS_STATIC: dict[str, str] = {
    "Content-Type": "application/json",
}
COPILOT_HEADERS_STATIC.update(build_copilot_ide_headers())

COPILOT_ERROR_BODY_LIMIT_BYTES = 8 * 1024
COPILOT_EMBEDDINGS_RESPONSE_MAX_BYTES = 64 * 1024 * 1024


def _is_copilot_setup_error(err: Any) -> bool:
    if not isinstance(err, Exception):
        return False
    msg = str(err)
    return any([
        "No GitHub token available" in msg,
        "Copilot token exchange failed" in msg,
        "Copilot token response" in msg,
        "No embedding models available" in msg,
        "GitHub Copilot model discovery" in msg,
        "github-copilot.model-discovery" in msg,
        "GitHub Copilot embedding model" in msg,
        "Unexpected response from GitHub Copilot token endpoint" in msg,
    ])


def _discover_embedding_models(params: dict[str, Any]) -> list[str]:
    import urllib.request
    base = params.get("baseUrl", "").rstrip("/")
    url = f"{base}/models"
    headers = dict(COPILOT_HEADERS_STATIC)
    headers.update(params.get("headers", {}))
    headers["Authorization"] = f"Bearer {params.get('copilotToken', '')}"

    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as res:
            if res.status != 200:
                return []
            body = res.read().decode("utf-8")
            payload = json.loads(body)
            data = payload.get("data", [])
            if not isinstance(data, list):
                return []

            result = []
            for entry in data:
                if not isinstance(entry, dict):
                    continue
                entry_id = entry.get("id", "")
                if not isinstance(entry_id, str):
                    continue
                entry_id = entry_id.strip()
                if not entry_id:
                    continue
                endpoints = entry.get("supported_endpoints", [])
                has_embedding_ep = False
                if isinstance(endpoints, list):
                    has_embedding_ep = any(
                        isinstance(ep, str) and "embeddings" in ep
                        for ep in endpoints
                    )
                if has_embedding_ep or "embedding" in entry_id.lower():
                    result.append(entry_id)
            return result
    except Exception:
        return []


def _pick_best_model(available: list[str], user_model: str | None = None) -> str:
    if user_model:
        normalized = user_model.strip()
        prefix = f"{COPILOT_EMBEDDING_PROVIDER_ID}/"
        stripped = normalized[len(prefix):] if normalized.startswith(prefix) else normalized
        if not available:
            raise ValueError("No embedding models available from GitHub Copilot")
        if stripped not in available:
            raise ValueError(
                f'GitHub Copilot embedding model "{stripped}" is not available. Available: {", ".join(available)}'
            )
        return stripped
    for preferred in PREFERRED_MODELS:
        if preferred in available:
            return preferred
    if available:
        return available[0]
    raise ValueError("No embedding models available from GitHub Copilot")


def _parse_embedding_payload(payload: Any, expected_count: int) -> list[list[float]]:
    if not isinstance(payload, dict):
        raise ValueError("GitHub Copilot embeddings response missing data[]")
    data = payload.get("data")
    if not isinstance(data, list):
        raise ValueError("GitHub Copilot embeddings response missing data[]")

    vectors: list[list[float] | None] = [None] * expected_count
    for entry in data:
        if not isinstance(entry, dict):
            raise ValueError("GitHub Copilot embeddings response contains an invalid entry")
        index_val = entry.get("index")
        embedding = entry.get("embedding")
        if not isinstance(index_val, int) or not (0 <= index_val < expected_count):
            raise ValueError("GitHub Copilot embeddings response contains an invalid index")
        if vectors[index_val] is not None:
            raise ValueError("GitHub Copilot embeddings response contains duplicate indexes")
        if not isinstance(embedding, list) or not all(isinstance(v, (int, float)) for v in embedding):
            raise ValueError("GitHub Copilot embeddings response contains an invalid embedding")
        vectors[index_val] = [float(v) for v in embedding]

    for i in range(expected_count):
        if vectors[i] is None:
            raise ValueError("GitHub Copilot embeddings response missing vectors for some inputs")

    return vectors  # type: ignore[return-value]


async def _resolve_embedding_session(client: dict[str, Any]) -> dict[str, Any]:
    token = await resolve_copilot_api_token({
        "githubToken": client.get("githubToken"),
        "env": client.get("env", os.environ),
    })
    base_url = (client.get("baseUrl") or token.get("baseUrl") or DEFAULT_COPILOT_API_BASE_URL).strip()
    return {
        "baseUrl": base_url,
        "headers": {
            **COPILOT_HEADERS_STATIC,
            **(client.get("headers") or {}),
            "Authorization": f"Bearer {token.get('token')}",
        },
    }


async def _create_embedding_provider(client: dict[str, Any]) -> dict[str, Any]:
    initial_session = await _resolve_embedding_session(client)

    async def embed(inputs: list[str]) -> list[list[float]]:
        if not inputs:
            return []
        session = await _resolve_embedding_session(client)
        import urllib.request
        url = f"{session['baseUrl'].rstrip('/')}/embeddings"
        body = json.dumps({"model": client.get("model"), "input": inputs}).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=body,
            headers=session["headers"],
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=30) as res:
            if res.status != 200:
                detail = res.read().decode("utf-8", errors="replace")[:COPILOT_ERROR_BODY_LIMIT_BYTES]
                raise RuntimeError(f"GitHub Copilot embeddings HTTP {res.status}: {detail}")
            resp_body = res.read().decode("utf-8")
            payload = json.loads(resp_body)
            return _parse_embedding_payload(payload, len(inputs))

    async def embed_query(text: str, options: dict[str, Any] | None = None) -> list[float]:
        vectors = await embed([text])
        return vectors[0] if vectors else []

    async def embed_batch(texts: list[str], options: dict[str, Any] | None = None) -> list[list[float]]:
        return await embed(texts)

    return {
        "provider": {
            "id": COPILOT_EMBEDDING_PROVIDER_ID,
            "model": client.get("model"),
            "embedQuery": embed_query,
            "embedBatch": embed_batch,
        },
        "client": {
            **client,
            "baseUrl": initial_session["baseUrl"],
        },
    }


github_copilot_memory_embedding_provider_adapter: dict[str, Any] = {
    "id": COPILOT_EMBEDDING_PROVIDER_ID,
    "transport": "remote",
    "authProviderId": COPILOT_EMBEDDING_PROVIDER_ID,
    "autoSelectPriority": 15,
    "allowExplicitWhenConfiguredAuto": True,
    "shouldContinueAutoSelection": lambda err: _is_copilot_setup_error(err),
    "create": async lambda options: await _create_embedding_provider_from_options(options),
}


async def _create_embedding_provider_from_options(options: dict[str, Any]) -> dict[str, Any]:
    remote_github_token = await resolve_configured_secret_input_string({
        "config": options.get("config"),
        "env": os.environ,
        "value": options.get("remote", {}).get("apiKey") if isinstance(options.get("remote"), dict) else None,
        "path": "agents.*.memorySearch.remote.apiKey",
    })
    resolved = await resolve_first_github_token({
        "agentDir": options.get("agentDir"),
        "config": options.get("config"),
        "env": os.environ,
    })
    profile_github_token = resolved.get("githubToken", "")
    github_token = (remote_github_token or {}).get("value", "") or profile_github_token
    if not github_token:
        raise ValueError("No GitHub token available for Copilot embedding provider")

    token_result = await resolve_copilot_api_token({
        "githubToken": github_token,
        "env": os.environ,
    })
    copilot_token = token_result.get("token", "")
    resolved_base_url = token_result.get("baseUrl", "")
    base_url = (
        (options.get("remote", {}) or {}).get("baseUrl", "") or resolved_base_url or DEFAULT_COPILOT_API_BASE_URL
    ).strip()

    available_models = _discover_embedding_models({
        "baseUrl": base_url,
        "copilotToken": copilot_token,
        "headers": (options.get("remote", {}) or {}).get("headers"),
    })

    user_model = (options.get("model") or "").strip() or None
    model = _pick_best_model(available_models, user_model)

    result = await _create_embedding_provider({
        "baseUrl": base_url,
        "env": os.environ,
        "githubToken": github_token,
        "headers": (options.get("remote", {}) or {}).get("headers"),
        "model": model,
    })

    return {
        "provider": result["provider"],
        "runtime": {
            "id": COPILOT_EMBEDDING_PROVIDER_ID,
            "cacheKeyData": {
                "provider": COPILOT_EMBEDDING_PROVIDER_ID,
                "baseUrl": base_url,
                "model": model,
            },
        },
    }
