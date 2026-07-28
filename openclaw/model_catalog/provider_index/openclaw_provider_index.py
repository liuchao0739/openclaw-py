from __future__ import annotations

from typing import Any

from .types import OpenClawProviderIndex

OPENCLAW_PROVIDER_INDEX: OpenClawProviderIndex = {
    "version": 1,
    "providers": {
        "moonshot": {
            "id": "moonshot",
            "name": "Moonshot AI",
            "plugin": {
                "id": "moonshot",
                "package": None,
                "source": None,
                "install": None,
            },
            "docs": "/providers/moonshot",
            "categories": ["cloud", "llm"],
            "authChoices": None,
            "previewCatalog": {
                "models": [
                    {
                        "id": "kimi-k2.6",
                        "name": "Kimi K2.6",
                        "input": ["text", "image"],
                        "contextWindow": 262144,
                    },
                    {
                        "id": "kimi-k2.7-code",
                        "name": "Kimi K2.7 Code",
                        "reasoning": True,
                        "input": ["text", "image"],
                        "contextWindow": 262144,
                    },
                ],
            },
        },
        "deepseek": {
            "id": "deepseek",
            "name": "DeepSeek",
            "plugin": {
                "id": "deepseek",
                "package": None,
                "source": None,
                "install": None,
            },
            "docs": "/providers/deepseek",
            "categories": ["cloud", "llm"],
            "authChoices": None,
            "previewCatalog": {
                "models": [
                    {
                        "id": "deepseek-chat",
                        "name": "DeepSeek Chat",
                        "input": ["text"],
                        "contextWindow": 131072,
                    },
                    {
                        "id": "deepseek-reasoner",
                        "name": "DeepSeek Reasoner",
                        "input": ["text"],
                        "reasoning": True,
                        "contextWindow": 131072,
                    },
                ],
            },
        },
    },
}


__all__ = [
    "OPENCLAW_PROVIDER_INDEX",
]
