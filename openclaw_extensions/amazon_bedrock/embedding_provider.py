from __future__ import annotations

import json
import os
import re
from typing import Any, Callable

from openclaw.plugin_sdk.memory_core_host_engine_embeddings import (
    debug_embeddings_log,
    sanitize_and_normalize_embedding,
    MemoryEmbeddingProvider,
    MemoryEmbeddingProviderCreateOptions,
)
from openclaw.plugin_sdk.string_coerce_runtime import (
    as_optional_record,
    normalize_lowercase_string_or_empty,
)
from openclaw_extensions.amazon_bedrock.aws_credential_refresh import (
    refresh_aws_shared_config_cache_for_bedrock,
)

DEFAULT_BEDROCK_EMBEDDING_MODEL = "amazon.titan-embed-text-v2:0"

_MODELS: dict[str, dict[str, Any]] = {
    "amazon.titan-embed-text-v2:0": {
        "maxTokens": 8192,
        "dims": 1024,
        "validDims": [256, 512, 1024],
        "family": "titan-v2",
    },
    "amazon.titan-embed-text-v1": {"maxTokens": 8000, "dims": 1536, "family": "titan-v1"},
    "amazon.titan-embed-g1-text-02": {"maxTokens": 8000, "dims": 1536, "family": "titan-v1"},
    "amazon.titan-embed-image-v1": {"maxTokens": 128, "dims": 1024, "family": "titan-v1"},
    "cohere.embed-english-v3": {"maxTokens": 512, "dims": 1024, "family": "cohere-v3"},
    "cohere.embed-multilingual-v3": {"maxTokens": 512, "dims": 1024, "family": "cohere-v3"},
    "cohere.embed-v4:0": {
        "maxTokens": 128000,
        "dims": 1536,
        "validDims": [256, 384, 512, 768, 1024, 1536],
        "family": "cohere-v4",
    },
    "amazon.nova-2-multimodal-embeddings-v1:0": {
        "maxTokens": 8192,
        "dims": 1024,
        "validDims": [256, 384, 1024, 3072],
        "family": "nova",
    },
    "twelvelabs.marengo-embed-2-7-v1:0": {"maxTokens": 512, "dims": 1024, "family": "twelvelabs"},
    "twelvelabs.marengo-embed-3-0-v1:0": {"maxTokens": 512, "dims": 512, "family": "twelvelabs"},
}

_MODEL_PREFIX_RE = re.compile(r"^(?:bedrock|amazon-bedrock|aws)/")
_REGION_RE = re.compile(r"bedrock-runtime\.([a-z0-9-]+)\.")


def _strip_inference_profile_prefix(model_id: str) -> str:
    return re.sub(r"^(?:us|eu|ap|apac|au|jp|global)\.", "", model_id)


def _resolve_spec(model_id: str) -> dict[str, Any] | None:
    bare = _strip_inference_profile_prefix(model_id)
    if bare in _MODELS:
        return _MODELS[bare]
    parts = bare.split(":")
    for i in range(len(parts) - 1, 0, -1):
        key = ":".join(parts[:i])
        if key in _MODELS:
            return _MODELS[key]
    return None


def _infer_family(model_id: str) -> str:
    id_lower = normalize_lowercase_string_or_empty(_strip_inference_profile_prefix(model_id))
    if id_lower.startswith("amazon.titan-embed-text-v2"):
        return "titan-v2"
    if id_lower.startswith("amazon.titan-embed"):
        return "titan-v1"
    if id_lower.startswith("amazon.nova"):
        return "nova"
    if id_lower.startswith("cohere.embed-v4"):
        return "cohere-v4"
    if id_lower.startswith("cohere.embed"):
        return "cohere-v3"
    if id_lower.startswith("twelvelabs."):
        return "twelvelabs"
    return "titan-v1"


def _normalize_bedrock_embedding_model(model: str) -> str:
    trimmed = model.strip()
    if not trimmed:
        return DEFAULT_BEDROCK_EMBEDDING_MODEL
    return _MODEL_PREFIX_RE.sub("", trimmed)


def _region_from_url(url: str | None) -> str | None:
    if url is None:
        return None
    trimmed = url.strip()
    if not trimmed:
        return None
    match = _REGION_RE.search(trimmed)
    return match.group(1) if match else None


def _build_body(family: str, text: str, dims: int | None = None) -> str:
    if family == "titan-v2":
        b: dict[str, Any] = {"inputText": text}
        if dims is not None:
            b["dimensions"] = dims
            b["normalize"] = True
        return json.dumps(b)
    if family == "titan-v1":
        return json.dumps({"inputText": text})
    if family == "nova":
        return json.dumps({
            "taskType": "SINGLE_EMBEDDING",
            "singleEmbeddingParams": {
                "embeddingPurpose": "GENERIC_INDEX",
                "embeddingDimension": dims or 1024,
                "text": {"truncationMode": "END", "value": text},
            },
        })
    if family == "twelvelabs":
        return json.dumps({"inputType": "text", "text": {"inputText": text}})
    return json.dumps({"inputText": text})


def _build_cohere_body(
    family: str,
    texts: list[str],
    input_type: str,
    dims: int | None = None,
) -> str:
    body: dict[str, Any] = {"texts": texts, "input_type": input_type, "truncate": "END"}
    if family == "cohere-v4":
        body["embedding_types"] = ["float"]
        if dims is not None:
            body["output_dimension"] = dims
    return json.dumps(body)


def _parse_single(family: str, raw: str) -> list[float]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")

    if not isinstance(data, dict):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")

    if family == "nova":
        embeddings = data.get("embeddings")
        if isinstance(embeddings, list) and embeddings:
            item = embeddings[0]
            if isinstance(item, dict):
                return _as_number_array(item.get("embedding"))
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
    if family == "twelvelabs":
        data_data = data.get("data")
        if isinstance(data_data, list) and data_data:
            first = as_optional_record(data_data[0])
            if first is not None and "embedding" in first:
                return _as_number_array(first["embedding"])
        if isinstance(data_data, dict):
            return _as_number_array(data_data.get("embedding"))
        return _as_number_array(data.get("embedding"))
    return _as_number_array(data.get("embedding"))


def _parse_cohere_batch(family: str, raw: str) -> list[list[float]]:
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, ValueError):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")

    if not isinstance(data, dict):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")

    embeddings = data.get("embeddings")
    if embeddings is None:
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")

    if family == "cohere-v4" and not isinstance(embeddings, list):
        embedding_record = as_optional_record(embeddings)
        if embedding_record is None:
            raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
        float_data = embedding_record.get("float")
        if not isinstance(float_data, list):
            raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
        return [_as_number_array(e) for e in float_data]

    if not isinstance(embeddings, list):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
    return [_as_number_array(e) for e in embeddings]


def _as_number_array(value: Any) -> list[float]:
    if not isinstance(value, list):
        raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
    result: list[float] = []
    for entry in value:
        if not isinstance(entry, (int, float)):
            raise ValueError("Amazon Bedrock embedding response returned malformed JSON")
        result.append(float(entry))
    return result


async def create_bedrock_embedding_provider(
    options: MemoryEmbeddingProviderCreateOptions,
) -> dict[str, Any]:
    model = _normalize_bedrock_embedding_model(options.get("model", ""))
    spec = _resolve_spec(model)
    family = spec.get("family") if spec else _infer_family(model)

    provider_config = options.get("config", {}).get("models", {}).get("providers", {}).get("amazon-bedrock", {})
    remote = options.get("remote")

    region = (
        _region_from_url(remote.get("baseUrl") if remote else None)
        or _region_from_url(provider_config.get("baseUrl") if provider_config else None)
        or os.environ.get("AWS_REGION")
        or os.environ.get("AWS_DEFAULT_REGION")
        or "us-east-1"
    )

    dimensions: int | None = None
    output_dimensionality = options.get("outputDimensionality")
    if output_dimensionality is not None:
        valid_dims = spec.get("validDims") if spec else None
        if valid_dims and output_dimensionality not in valid_dims:
            raise ValueError(
                f"Invalid dimensions {output_dimensionality} for {model}. Valid values: {', '.join(str(d) for d in valid_dims)}"
            )
        dimensions = output_dimensionality
    elif spec:
        dimensions = spec.get("dims")

    client = {
        "region": region,
        "model": model,
        "dimensions": dimensions,
    }

    debug_embeddings_log("memory embeddings: bedrock client", {
        "region": region,
        "model": model,
        "dimensions": dimensions,
        "family": family,
    })

    is_cohere = family in ("cohere-v3", "cohere-v4")

    async def invoke(body: str, signal: Any = None) -> str:
        await refresh_aws_shared_config_cache_for_bedrock()
        try:
            from bedrock_runtime import BedrockRuntimeClient, InvokeModelCommand
        except ImportError:
            raise ValueError(
                "No API key found for provider bedrock: bedrock_runtime is not installed. "
                "Install it with: pip install bedrock-runtime"
            )
        sdk = BedrockRuntimeClient({"region": client["region"]})
        try:
            res = sdk.send(
                InvokeModelCommand({
                    "modelId": client["model"],
                    "body": body,
                    "contentType": "application/json",
                    "accept": "application/json",
                }),
                {"abortSignal": signal} if signal else None,
            )
            return res["body"].decode("utf-8")
        finally:
            sdk.destroy()

    async def embed_single(text: str, signal: Any = None) -> list[float]:
        raw = await invoke(_build_body(family, text, client.get("dimensions")), signal)
        return sanitize_and_normalize_embedding(_parse_single(family, raw))

    async def embed_cohere(
        texts: list[str],
        input_type: str,
        signal: Any = None,
    ) -> list[list[float]]:
        raw = await invoke(_build_cohere_body(family, texts, input_type, client.get("dimensions")), signal)
        return [sanitize_and_normalize_embedding(e) for e in _parse_cohere_batch(family, raw)]

    async def embed_query(text: str, options_value: dict[str, Any] | None = None) -> list[float]:
        if not text.strip():
            return []
        signal = options_value.get("signal") if options_value else None
        if is_cohere:
            results = await embed_cohere([text], "search_query", signal)
            return results[0] if results else []
        return await embed_single(text, signal)

    async def embed_batch(
        texts: list[str],
        options_local: dict[str, Any] | None = None,
    ) -> list[list[float]]:
        if not texts:
            return []
        signal = options_local.get("signal") if options_local else None
        if is_cohere:
            return await embed_cohere(texts, "search_document", signal)
        results = await __import__("asyncio").gather(
            *(embed_single(t, signal) if t.strip() else __import__("asyncio").coroutine(lambda: [])() for t in texts)
        )
        return list(results)

    provider: MemoryEmbeddingProvider = {
        "id": "bedrock",
        "model": client["model"],
        "maxInputTokens": spec.get("maxTokens") if spec else None,
        "embedQuery": embed_query,
        "embedBatch": embed_batch,
    }

    return {
        "provider": provider,
        "client": client,
    }


async def has_aws_credentials(
    env: dict[str, str] | None = None,
) -> bool:
    if env is None:
        env = os.environ
    if env.get("AWS_ACCESS_KEY_ID", "").strip() and env.get("AWS_SECRET_ACCESS_KEY", "").strip():
        return True
    if env.get("AWS_BEARER_TOKEN_BEDROCK", "").strip():
        return True
    return False


__all__ = [
    "DEFAULT_BEDROCK_EMBEDDING_MODEL",
    "create_bedrock_embedding_provider",
    "has_aws_credentials",
]