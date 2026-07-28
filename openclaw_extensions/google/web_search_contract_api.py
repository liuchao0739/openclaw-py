from typing import Optional, Dict, Any, List

from .config_defaults import GoogleConfigDefaults
from .web_search_provider import GoogleWebSearchProvider


class GoogleWebSearchContractAPI:
    def __init__(self, config: Optional[GoogleConfigDefaults] = None):
        self.config = config
        self._provider = GoogleWebSearchProvider(config=config)

    def get_contract(self) -> Dict[str, Any]:
        return {
            "provider": "google",
            "tool_name": "web_search",
            "tool_description": "Search the web for information using Google Search",
            "input_schema": {
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
            "output_schema": {
                "type": "object",
                "properties": {
                    "answer": {
                        "type": "string",
                        "description": "The generated answer with citations",
                    },
                    "citations": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "uri": {"type": "string"},
                                "startIndex": {"type": "integer"},
                                "endIndex": {"type": "integer"},
                            },
                        },
                    },
                    "sources": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "uri": {"type": "string"},
                            },
                        },
                    },
                },
            },
            "supported_models": self._provider.get_supported_models(),
        }

    def validate_contract(self) -> Dict[str, Any]:
        contract = self.get_contract()
        return {
            "valid": True,
            "tool_name": contract.get("tool_name"),
            "has_input_schema": bool(contract.get("input_schema")),
            "has_output_schema": bool(contract.get("output_schema")),
            "supported_models": len(contract.get("supported_models", [])),
        }

    def get_tool_definition(self) -> Dict[str, Any]:
        return self._provider.get_tool_definition()

    def execute_contract(
        self,
        query: str,
        max_results: int = 10,
    ) -> Dict[str, Any]:
        result = self._provider.search(query, max_results)
        return result.to_dict()