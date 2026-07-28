import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import (
    resolve_google_api_key_from_environment,
    resolve_google_generative_ai_http_request_config,
    parse_gemini_auth,
)


@dataclass
class GoogleEmbeddingRequest:
    model: str
    text: str
    task_type: Optional[str] = None
    title: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        result = {
            "model": self.model,
            "content": {"parts": [{"text": self.text}]},
        }
        if self.task_type:
            result["taskType"] = self.task_type
        if self.title:
            result["title"] = self.title
        return result


@dataclass
class GoogleEmbeddingResponse:
    embedding: List[float]
    model: str
    dimension: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "embedding": self.embedding,
            "model": self.model,
            "dimension": self.dimension,
        }


class GoogleEmbeddingProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/text-embedding-005"

    def initialize(self) -> None:
        auth = parse_gemini_auth(self.config)
        self._api_key = auth.get("api_key")
        request_config = resolve_google_generative_ai_http_request_config(
            config=self.config,
        )
        self._base_url = request_config.get("base_url", self._base_url)

    def set_model(self, model: str) -> None:
        self._model = model

    def get_model(self) -> str:
        return self._model

    def embed(self, text: str, task_type: Optional[str] = None) -> GoogleEmbeddingResponse:
        import urllib.request
        import urllib.error

        self.initialize()

        request = GoogleEmbeddingRequest(
            model=self._model,
            text=text,
            task_type=task_type,
        )

        url = f"{self._base_url}/v1beta/models/{self._model}:embedText"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request.to_dict()).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                embedding_data = response_data.get("embedding", {})
                return GoogleEmbeddingResponse(
                    embedding=embedding_data.get("values", []),
                    model=self._model,
                    dimension=len(embedding_data.get("values", [])),
                )
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Embedding API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Embedding API connection error: {e.reason}")

    def embed_batch(
        self,
        texts: List[str],
        task_type: Optional[str] = None,
    ) -> List[GoogleEmbeddingResponse]:
        import urllib.request
        import urllib.error

        self.initialize()

        request_body: Dict[str, Any] = {
            "model": self._model,
        }

        content_list = []
        for text in texts:
            content_list.append({"parts": [{"text": text}]})

        request_body["content"] = content_list
        if task_type:
            request_body["taskType"] = task_type

        url = f"{self._base_url}/v1beta/models/{self._model}:batchEmbedContents"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request_body).encode("utf-8")

        headers = {
            "Content-Type": "application/json",
        }

        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=120) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                embeddings = response_data.get("embeddings", [])
                results = []
                for emb in embeddings:
                    results.append(GoogleEmbeddingResponse(
                        embedding=emb.get("values", []),
                        model=self._model,
                        dimension=len(emb.get("values", [])),
                    ))
                return results
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Batch Embedding API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Batch Embedding API connection error: {e.reason}")


def create_google_embedding_provider(config: Optional[GoogleConfigDefaults] = None) -> GoogleEmbeddingProvider:
    return GoogleEmbeddingProvider(config=config)