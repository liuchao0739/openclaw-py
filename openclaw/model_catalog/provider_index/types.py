from __future__ import annotations

from typing import Literal, TypedDict

from openclaw_packages.model_catalog_core.model_catalog_types import ModelCatalogProvider


class OpenClawProviderIndexPluginInstall(TypedDict, total=False):
    clawhubSpec: str
    npmSpec: str
    defaultChoice: Literal["clawhub", "npm"]
    minHostVersion: str
    expectedIntegrity: str


class OpenClawProviderIndexPlugin(TypedDict):
    id: str
    package: str | None
    source: str | None
    install: OpenClawProviderIndexPluginInstall | None


class OpenClawProviderIndexProviderAuthChoice(TypedDict, total=False):
    method: str
    choiceId: str
    choiceLabel: str
    choiceHint: str
    assistantPriority: float
    assistantVisibility: Literal["visible", "manual-only"]
    groupId: str
    groupLabel: str
    groupHint: str
    optionKey: str
    cliFlag: str
    cliOption: str
    cliDescription: str
    onboardingScopes: list[Literal["text-inference", "image-generation", "music-generation"]]


class OpenClawProviderIndexProvider(TypedDict):
    id: str
    name: str
    plugin: OpenClawProviderIndexPlugin
    docs: str | None
    categories: list[str] | None
    authChoices: list[OpenClawProviderIndexProviderAuthChoice] | None
    previewCatalog: ModelCatalogProvider | None


class OpenClawProviderIndex(TypedDict):
    version: int
    providers: dict[str, OpenClawProviderIndexProvider]


__all__ = [
    "OpenClawProviderIndex",
    "OpenClawProviderIndexPlugin",
    "OpenClawProviderIndexPluginInstall",
    "OpenClawProviderIndexProvider",
    "OpenClawProviderIndexProviderAuthChoice",
]
