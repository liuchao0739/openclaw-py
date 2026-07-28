import os
import json
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

from .config_defaults import GoogleConfigDefaults
from .gemini_auth import resolve_google_api_key_from_environment


@dataclass
class WebSearchRequest:
    query: str
    model: str = "google/gemini-2.5-pro"
    max_results: int = 10
    include_answer: bool = True
    include_citations: bool = True
    language: Optional[str] = None
    region: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "contents": [{"text": self.query}],
            "tools": [{"web_search": {}}],
            "generationConfig": {
                "candidateCount": 1,
            },
        }


@dataclass
class WebSearchResult:
    query: str
    answer: Optional[str] = None
    citations: List[Dict[str, Any]] = None
    sources: List[Dict[str, Any]] = None
    model: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "query": self.query,
            "answer": self.answer,
            "citations": self.citations,
            "sources": self.sources,
            "model": self.model,
        }


class GoogleWebSearchProvider:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._api_key: Optional[str] = None
        self._base_url: str = "https://generativelanguage.googleapis.com"
        self._model: str = "google/gemini-2.5-pro"
        self._initialized = False

    def initialize(self) -> None:
        if self._initialized:
            return
        self._api_key = resolve_google_api_key_from_environment()
        if self.config and self.config.google_generative_ai_http_base_url:
            self._base_url = self.config.google_generative_ai_http_base_url
        if self.config and self.config.google_api_key:
            self._api_key = self.config.google_api_key
        self._initialized = True

    def set_model(self, model: str) -> None:
        self._model = model

    def search(
        self,
        query: str,
        max_results: int = 10,
        include_answer: bool = True,
    ) -> WebSearchResult:
        import urllib.request
        import urllib.error

        self.initialize()

        request = WebSearchRequest(
            query=query,
            model=self._model,
            max_results=max_results,
            include_answer=include_answer,
        )

        model_name = self._model.replace("google/", "")
        url = f"{self._base_url}/v1beta/models/{model_name}:generateContent"
        if self._api_key:
            url += f"?key={self._api_key}"

        data = json.dumps(request.to_dict()).encode("utf-8")
        headers = {"Content-Type": "application/json"}
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")

        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                response_data = json.loads(resp.read().decode("utf-8"))
                return self._parse_response(response_data, query)
        except urllib.error.HTTPError as e:
            error_body = e.read().decode("utf-8") if e.fp else ""
            raise RuntimeError(f"Google Web Search API error: {e.code} - {error_body}")
        except urllib.error.URLError as e:
            raise RuntimeError(f"Google Web Search API connection error: {e.reason}")

    def _parse_response(
        self,
        response_data: Dict[str, Any],
        query: str,
    ) -> WebSearchResult:
        result = WebSearchResult(query=query, model=self._model)

        candidates = response_data.get("candidates", [])
        if not candidates:
            return result

        content = candidates[0].get("content", {})
        parts = content.get("parts", [])

        text_parts = []
        for part in parts:
            if "text" in part:
                text_parts.append(part["text"])

        result.answer = "\n".join(text_parts)

        citations = []
        for part in parts:
            if "citationMetadata" in part:
                metadata = part["citationMetadata"]
                citation_sources = metadata.get("citationSources", [])
                for source in citation_sources:
                    citations.append({
                        "startIndex": source.get("startIndex"),
                        "endIndex": source.get("endIndex"),
                        "uri": source.get("uri"),
                        "license_": source.get("license"),
                    })

        result.citations = citations
        result.sources = citations
        return result

    def get_supported_models(self) -> List[str]:
        return [
            "google/gemini-2.5-pro",
            "google/gemini-2.0-flash",
            "google/gemini-1.5-pro",
            "google/gemini-1.5-flash",
        ]

    def get_tool_definition(self) -> Dict[str, Any]:
        return {
            "type": "function",
            "function": {
                "name": "web_search",
                "description": "Search the web for information using Google Search",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string",
                            "description": "The search query",
                        },
                        "max_results": {
                            "type": "integer",
                            "description": "Maximum number of results to return",
                            "default": 10,
                        },
                    },
                    "required": ["query"],
                },
            },
        }