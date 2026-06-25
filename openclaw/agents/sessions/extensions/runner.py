"""Extension runner — executes extensions and manages their lifecycle.

This port provides the ExtensionRunner class with emit/has_handlers/create_context
methods and the key event dispatch patterns from the TypeScript version.
"""

from __future__ import annotations

import copy
from typing import Any

from openclaw.agents.sessions.extensions.types import (
    RESERVED_KEYBINDINGS_FOR_EXTENSION_CONFLICTS,
    Extension,
    ExtensionError,
    ExtensionFlag,
)


class ExtensionRunner:
    """Executes extensions and manages their lifecycle."""

    def __init__(
        self,
        extensions: list[Extension],
        runtime: dict[str, Any],
        cwd: str,
        session_manager: Any = None,
        model_registry: Any = None,
    ) -> None:
        self._extensions = extensions
        self._runtime = runtime
        self._cwd = cwd
        self._session_manager = session_manager
        self._model_registry = model_registry
        self._error_listeners: list[Any] = []
        self._stale_message: str | None = None
        self._shortcut_diagnostics: list[dict[str, Any]] = []
        self._command_diagnostics: list[dict[str, Any]] = []
        # Context action stubs
        self._get_model: Any = lambda: None
        self._is_idle: Any = lambda: True
        self._get_signal: Any = lambda: None
        self._abort: Any = lambda: None
        self._has_pending_messages: Any = lambda: False
        self._shutdown_handler: Any = lambda: None
        self._get_context_usage: Any = lambda: None
        self._compact: Any = lambda options=None: None
        self._get_system_prompt: Any = lambda: ""

    def bind_core(
        self,
        actions: dict[str, Any],
        context_actions: dict[str, Any],
        provider_actions: dict[str, Any] | None = None,
    ) -> None:
        """Copy actions into the shared runtime and flush pending provider registrations."""
        for key in (
            "sendMessage", "sendUserMessage", "appendEntry", "setSessionName",
            "getSessionName", "setLabel", "getActiveTools", "getAllTools",
            "setActiveTools", "refreshTools", "getCommands", "setModel",
            "getThinkingLevel", "setThinkingLevel",
        ):
            if key in actions:
                self._runtime[key] = actions[key]

        self._get_model = context_actions.get("getModel", self._get_model)
        self._is_idle = context_actions.get("isIdle", self._is_idle)
        self._get_signal = context_actions.get("getSignal", self._get_signal)
        self._abort = context_actions.get("abort", self._abort)
        self._has_pending_messages = context_actions.get("hasPendingMessages", self._has_pending_messages)
        self._shutdown_handler = context_actions.get("shutdown", self._shutdown_handler)
        self._get_context_usage = context_actions.get("getContextUsage", self._get_context_usage)
        self._compact = context_actions.get("compact", self._compact)
        self._get_system_prompt = context_actions.get("getSystemPrompt", self._get_system_prompt)

        # Flush pending provider registrations
        for reg in self._runtime.get("pendingProviderRegistrations", []):
            try:
                if provider_actions and provider_actions.get("registerProvider"):
                    provider_actions["registerProvider"](reg["name"], reg["config"])
                elif self._model_registry and hasattr(self._model_registry, "registerProvider"):
                    self._model_registry.registerProvider(reg["name"], reg["config"])
            except Exception as err:
                self.emit_error({
                    "extensionPath": reg.get("extensionPath", ""),
                    "event": "register_provider",
                    "error": str(err),
                })
        self._runtime["pendingProviderRegistrations"] = []

        def _register_provider(name: str, config: dict[str, Any]) -> None:
            if provider_actions and provider_actions.get("registerProvider"):
                provider_actions["registerProvider"](name, config)
                return
            if self._model_registry and hasattr(self._model_registry, "registerProvider"):
                self._model_registry.registerProvider(name, config)

        def _unregister_provider(name: str) -> None:
            if provider_actions and provider_actions.get("unregisterProvider"):
                provider_actions["unregisterProvider"](name)
                return
            if self._model_registry and hasattr(self._model_registry, "unregisterProvider"):
                self._model_registry.unregisterProvider(name)

        self._runtime["registerProvider"] = _register_provider
        self._runtime["unregisterProvider"] = _unregister_provider

    def get_extension_paths(self) -> list[str]:
        return [e["path"] for e in self._extensions]

    def get_all_registered_tools(self) -> list[dict[str, Any]]:
        """Get all registered tools (first registration per name wins)."""
        tools_by_name: dict[str, dict[str, Any]] = {}
        for ext in self._extensions:
            for name, tool in ext.get("tools", {}).items():
                if name not in tools_by_name:
                    tools_by_name[name] = tool
        return list(tools_by_name.values())

    def get_tool_definition(self, tool_name: str) -> dict[str, Any] | None:
        for ext in self._extensions:
            tool = ext.get("tools", {}).get(tool_name)
            if tool:
                return tool["definition"]
        return None

    def get_flags(self) -> dict[str, ExtensionFlag]:
        all_flags: dict[str, ExtensionFlag] = {}
        for ext in self._extensions:
            for name, flag in ext.get("flags", {}).items():
                if name not in all_flags:
                    all_flags[name] = flag
        return all_flags

    def set_flag_value(self, name: str, value: bool | str) -> None:
        self._runtime["flagValues"][name] = value

    def get_flag_values(self) -> dict[str, bool | str]:
        return dict(self._runtime.get("flagValues", {}))

    def get_shortcuts(self, resolved_keybindings: dict[str, Any]) -> dict[str, Any]:
        self._shortcut_diagnostics = []
        extension_shortcuts: dict[str, Any] = {}

        for ext in self._extensions:
            for key, shortcut in ext.get("shortcuts", {}).items():
                normalized_key = key.lower()
                extension_shortcuts[normalized_key] = shortcut
        return extension_shortcuts

    def get_shortcut_diagnostics(self) -> list[dict[str, Any]]:
        return self._shortcut_diagnostics

    def invalidate(self, message: str | None = None) -> None:
        if not self._stale_message:
            self._stale_message = message or (
                "This extension ctx is stale after session replacement or reload."
            )
            self._runtime["invalidate"](self._stale_message)

    def _assert_active(self) -> None:
        if self._stale_message:
            raise RuntimeError(self._stale_message)

    def on_error(self, listener: Any) -> Any:
        self._error_listeners.append(listener)
        return lambda: self._error_listeners.remove(listener) if listener in self._error_listeners else None

    def emit_error(self, error: ExtensionError) -> None:
        for listener in self._error_listeners:
            listener(error)

    def has_handlers(self, event_type: str) -> bool:
        for ext in self._extensions:
            handlers = ext.get("handlers", {}).get(event_type)
            if handlers:
                return True
        return False

    def get_message_renderer(self, custom_type: str) -> Any | None:
        for ext in self._extensions:
            renderer = ext.get("messageRenderers", {}).get(custom_type)
            if renderer:
                return renderer
        return None

    def create_context(self) -> dict[str, Any]:
        """Create an ExtensionContext for use in event handlers and tool execution."""
        runner = self

        class _Context:
            @property
            def ui(self) -> Any:
                runner._assert_active()
                return None

            @property
            def hasUI(self) -> bool:
                runner._assert_active()
                return False

            @property
            def cwd(self) -> str:
                runner._assert_active()
                return runner._cwd

            @property
            def sessionManager(self) -> Any:
                runner._assert_active()
                return runner._session_manager

            @property
            def modelRegistry(self) -> Any:
                runner._assert_active()
                return runner._model_registry

            @property
            def model(self) -> Any:
                runner._assert_active()
                return runner._get_model()

            def isIdle(self) -> bool:
                runner._assert_active()
                return runner._is_idle()

            @property
            def signal(self) -> Any:
                runner._assert_active()
                return runner._get_signal()

            def abort(self) -> None:
                runner._assert_active()
                runner._abort()

            def hasPendingMessages(self) -> bool:
                runner._assert_active()
                return runner._has_pending_messages()

            def shutdown(self) -> None:
                runner._assert_active()
                runner._shutdown_handler()

            def getContextUsage(self) -> Any:
                runner._assert_active()
                return runner._get_context_usage()

            def compact(self, options: Any = None) -> None:
                runner._assert_active()
                runner._compact(options)

            def getSystemPrompt(self) -> str:
                runner._assert_active()
                return runner._get_system_prompt()

        return _Context()  # type: ignore[return-value]

    async def emit(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Emit an event to all extensions, returning the last session-before result."""
        ctx = self.create_context()
        result: dict[str, Any] | None = None
        event_type = event.get("type", "")

        for ext in self._extensions:
            handlers = ext.get("handlers", {}).get(event_type, [])
            for handler in handlers:
                try:
                    handler_result = handler(event, ctx)
                    if hasattr(handler_result, "__await__"):
                        handler_result = await handler_result
                    if handler_result and isinstance(handler_result, dict):
                        if event_type.startswith("session_before_"):
                            result = handler_result
                            if result.get("cancel"):
                                return result
                except Exception as err:
                    self.emit_error({
                        "extensionPath": ext["path"],
                        "event": event_type,
                        "error": str(err),
                    })
        return result

    async def emit_tool_call(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Emit tool_call event, returning block result if any handler blocks."""
        ctx = self.create_context()
        result: dict[str, Any] | None = None

        for ext in self._extensions:
            handlers = ext.get("handlers", {}).get("tool_call", [])
            for handler in handlers:
                handler_result = handler(event, ctx)
                if hasattr(handler_result, "__await__"):
                    handler_result = await handler_result
                if handler_result and isinstance(handler_result, dict):
                    result = handler_result
                    if result.get("block"):
                        return result
        return result

    async def emit_tool_result(self, event: dict[str, Any]) -> dict[str, Any] | None:
        """Emit tool_result event, returning modified content/details if any handler changes them."""
        ctx = self.create_context()
        current_event = {**event}
        modified = False

        for ext in self._extensions:
            handlers = ext.get("handlers", {}).get("tool_result", [])
            for handler in handlers:
                try:
                    handler_result = handler(current_event, ctx)
                    if hasattr(handler_result, "__await__"):
                        handler_result = await handler_result
                    if not handler_result:
                        continue
                    if handler_result.get("content") is not None:
                        current_event["content"] = handler_result["content"]
                        modified = True
                    if handler_result.get("details") is not None:
                        current_event["details"] = handler_result["details"]
                        modified = True
                    if handler_result.get("isError") is not None:
                        current_event["isError"] = handler_result["isError"]
                        modified = True
                except Exception as err:
                    self.emit_error({
                        "extensionPath": ext["path"],
                        "event": "tool_result",
                        "error": str(err),
                    })

        if not modified:
            return None
        return {
            "content": current_event.get("content"),
            "details": current_event.get("details"),
            "isError": current_event.get("isError"),
        }

    async def emit_context(self, messages: list[Any]) -> list[Any]:
        """Emit context event, allowing handlers to modify messages."""
        ctx = self.create_context()
        current_messages = copy.deepcopy(messages)

        for ext in self._extensions:
            handlers = ext.get("handlers", {}).get("context", [])
            for handler in handlers:
                try:
                    event = {"type": "context", "messages": current_messages}
                    handler_result = handler(event, ctx)
                    if hasattr(handler_result, "__await__"):
                        handler_result = await handler_result
                    if handler_result and isinstance(handler_result, dict) and handler_result.get("messages"):
                        current_messages = handler_result["messages"]
                except Exception as err:
                    self.emit_error({
                        "extensionPath": ext["path"],
                        "event": "context",
                        "error": str(err),
                    })
        return current_messages

    async def emit_input(
        self,
        text: str,
        images: list[Any] | None,
        source: str,
    ) -> dict[str, Any]:
        """Emit input event. Transforms chain, 'handled' short-circuits."""
        ctx = self.create_context()
        current_text = text
        current_images = images

        for ext in self._extensions:
            for handler in ext.get("handlers", {}).get("input", []):
                try:
                    event = {
                        "type": "input",
                        "text": current_text,
                        "images": current_images,
                        "source": source,
                    }
                    result = handler(event, ctx)
                    if hasattr(result, "__await__"):
                        result = await result
                    if result and result.get("action") == "handled":
                        return result
                    if result and result.get("action") == "transform":
                        current_text = result.get("text", current_text)
                        current_images = result.get("images", current_images)
                except Exception as err:
                    self.emit_error({
                        "extensionPath": ext["path"],
                        "event": "input",
                        "error": str(err),
                    })
        if current_text != text or current_images is not images:
            return {"action": "transform", "text": current_text, "images": current_images}
        return {"action": "continue"}


async def emit_session_shutdown_event(
    extension_runner: ExtensionRunner,
    event: dict[str, Any],
) -> bool:
    """Emit session_shutdown event. Returns True if handlers exist."""
    if extension_runner.has_handlers("session_shutdown"):
        await extension_runner.emit(event)
        return True
    return False
