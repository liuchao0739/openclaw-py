"""Captured plugin registration helpers for extension entry tests."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class CapturedPluginRegistration:
    """Registration captures from a plugin entry register() call."""

    api: Any
    tools: list[Any] = field(default_factory=list)
    providers: list[Any] = field(default_factory=list)
    media_understanding_providers: list[Any] = field(default_factory=list)
    video_generation_providers: list[Any] = field(default_factory=list)
    runtime_lifecycles: list[dict[str, Any]] = field(default_factory=list)


class _CapturedPluginLifecycleApi:
    def __init__(self, runtime_lifecycles: list[dict[str, Any]]) -> None:
        self._runtime_lifecycles = runtime_lifecycles

    def register_runtime_lifecycle(self, lifecycle: dict[str, Any]) -> None:
        self._runtime_lifecycles.append(lifecycle)


class _CapturedPluginApi:
    def __init__(
        self,
        *,
        plugin_id: str,
        tools: list[Any],
        providers: list[Any],
        media_understanding_providers: list[Any],
        video_generation_providers: list[Any],
        runtime_lifecycles: list[dict[str, Any]],
    ) -> None:
        self.id = plugin_id
        self.plugin_config: dict[str, Any] | None = None
        self.lifecycle = _CapturedPluginLifecycleApi(runtime_lifecycles)
        self._tools = tools
        self._providers = providers
        self._media_understanding_providers = media_understanding_providers
        self._video_generation_providers = video_generation_providers

    def register_tool(self, tool: Any, *_args: Any, **_kwargs: Any) -> None:
        if not callable(tool):
            self._tools.append(tool)

    def register_provider(self, provider: Any) -> None:
        self._providers.append(provider)

    def register_media_understanding_provider(self, provider: Any) -> None:
        self._media_understanding_providers.append(provider)

    def register_video_generation_provider(self, provider: Any) -> None:
        self._video_generation_providers.append(provider)


def create_captured_plugin_registration(
    *,
    id: str = "captured-plugin-registration",
    **_kwargs: Any,
) -> CapturedPluginRegistration:
    """Build a fake plugin API that records tools and runtime lifecycles."""
    tools: list[Any] = []
    providers: list[Any] = []
    media_understanding_providers: list[Any] = []
    video_generation_providers: list[Any] = []
    runtime_lifecycles: list[dict[str, Any]] = []
    api = _CapturedPluginApi(
        plugin_id=id,
        tools=tools,
        providers=providers,
        media_understanding_providers=media_understanding_providers,
        video_generation_providers=video_generation_providers,
        runtime_lifecycles=runtime_lifecycles,
    )
    return CapturedPluginRegistration(
        api=api,
        tools=tools,
        providers=providers,
        media_understanding_providers=media_understanding_providers,
        video_generation_providers=video_generation_providers,
        runtime_lifecycles=runtime_lifecycles,
    )
