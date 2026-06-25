"""Extension loader — loads extension modules and creates extension runtime state.

The TypeScript version uses jiti for source-transform loading. This Python port
provides the runtime state factory, extension object creation, and a load
function that accepts factory functions directly (Python extension loading is
done via importlib, not jiti).
"""

from __future__ import annotations

from typing import Any

from openclaw.agents.sessions.extensions.types import (
    Extension,
    LoadExtensionsResult,
    create_synthetic_source_info,
)


def create_extension_runtime() -> dict[str, Any]:
    """Create a runtime with throwing stubs for action methods.

    Runner.bind_core() replaces these with real implementations.
    """
    state: dict[str, Any] = {"staleMessage": None}

    def assert_active() -> None:
        if state["staleMessage"]:
            raise RuntimeError(state["staleMessage"])

    def invalidate(message: str | None = None) -> None:
        if state["staleMessage"] is None:
            state["staleMessage"] = message or (
                "This extension ctx is stale after session replacement or reload."
            )

    runtime: dict[str, Any] = {
        "sendMessage": _not_initialized,
        "sendUserMessage": _not_initialized,
        "appendEntry": _not_initialized,
        "setSessionName": _not_initialized,
        "getSessionName": _not_initialized,
        "setLabel": _not_initialized,
        "getActiveTools": _not_initialized,
        "getAllTools": _not_initialized,
        "setActiveTools": _not_initialized,
        "refreshTools": lambda: None,
        "getCommands": _not_initialized,
        "setModel": lambda model: _reject_not_initialized(),
        "getThinkingLevel": _not_initialized,
        "setThinkingLevel": _not_initialized,
        "flagValues": {},
        "pendingProviderRegistrations": [],
        "assertActive": assert_active,
        "invalidate": invalidate,
        "registerProvider": lambda name, config, extension_path="<unknown>": runtime[
            "pendingProviderRegistrations"
        ].append({"name": name, "config": config, "extensionPath": extension_path}),
        "unregisterProvider": lambda name: _unregister_provider(runtime, name),
    }
    return runtime


def _not_initialized(*_args: Any, **_kwargs: Any) -> Any:
    raise RuntimeError(
        "Extension runtime not initialized. Action methods cannot be called during extension loading."
    )


async def _reject_not_initialized() -> Any:
    raise RuntimeError(
        "Extension runtime not initialized. Action methods cannot be called during extension loading."
    )


def _unregister_provider(runtime: dict[str, Any], name: str) -> None:
    runtime["pendingProviderRegistrations"] = [
        r for r in runtime["pendingProviderRegistrations"] if r["name"] != name
    ]


def _create_extension(extension_path: str, resolved_path: str) -> Extension:
    """Create an Extension object with empty collections."""
    source = (
        extension_path[1:-1].split(":")[0] or "temporary"
        if extension_path.startswith("<") and extension_path.endswith(">")
        else "local"
    )
    base_dir = None if extension_path.startswith("<") else _dirname(resolved_path)
    return Extension(
        path=extension_path,
        resolvedPath=resolved_path,
        sourceInfo=create_synthetic_source_info(extension_path, {"source": source, "baseDir": base_dir}),
        handlers={},
        tools={},
        messageRenderers={},
        commands={},
        flags={},
        shortcuts={},
    )


def _dirname(path: str) -> str:
    import os

    return os.path.dirname(path)


def _create_extension_api(
    extension: Extension,
    runtime: dict[str, Any],
    cwd: str,
    event_bus: Any,
) -> dict[str, Any]:
    """Create the ExtensionAPI for an extension."""

    def _on(event: str, handler: Any) -> None:
        runtime["assertActive"]()
        handlers = extension.get("handlers", {}).get(event, [])
        handlers.append(handler)
        extension.setdefault("handlers", {})[event] = handlers

    def _register_tool(tool: dict[str, Any]) -> None:
        runtime["assertActive"]()
        extension.setdefault("tools", {})[tool["name"]] = {
            "definition": tool,
            "sourceInfo": extension.get("sourceInfo"),
        }
        runtime["refreshTools"]()

    def _register_command(name: str, options: dict[str, Any]) -> None:
        runtime["assertActive"]()
        extension.setdefault("commands", {})[name] = {
            "name": name,
            "sourceInfo": extension.get("sourceInfo"),
            **options,
        }

    def _register_flag(name: str, options: dict[str, Any]) -> None:
        runtime["assertActive"]()
        extension.setdefault("flags", {})[name] = {"name": name, "extensionPath": extension["path"], **options}
        if options.get("default") is not None and name not in runtime["flagValues"]:
            runtime["flagValues"][name] = options["default"]

    def _get_flag(name: str) -> bool | str | None:
        runtime["assertActive"]()
        if name not in extension.get("flags", {}):
            return None
        return runtime["flagValues"].get(name)

    api: dict[str, Any] = {
        "on": _on,
        "registerTool": _register_tool,
        "registerCommand": _register_command,
        "registerShortcut": lambda shortcut, options: _register_shortcut(extension, runtime, shortcut, options),
        "registerFlag": _register_flag,
        "registerMessageRenderer": lambda custom_type, renderer: _register_message_renderer(extension, runtime, custom_type, renderer),
        "getFlag": _get_flag,
        "sendMessage": lambda message, options=None: _delegate(runtime, "sendMessage", message, options),
        "sendUserMessage": lambda content, options=None: _delegate(runtime, "sendUserMessage", content, options),
        "appendEntry": lambda custom_type, data=None: _delegate(runtime, "appendEntry", custom_type, data),
        "setSessionName": lambda name: _delegate(runtime, "setSessionName", name),
        "getSessionName": lambda: _delegate(runtime, "getSessionName"),
        "setLabel": lambda entry_id, label: _delegate(runtime, "setLabel", entry_id, label),
        "getActiveTools": lambda: _delegate(runtime, "getActiveTools"),
        "getAllTools": lambda: _delegate(runtime, "getAllTools"),
        "setActiveTools": lambda tool_names: _delegate(runtime, "setActiveTools", tool_names),
        "getCommands": lambda: _delegate(runtime, "getCommands"),
        "setModel": lambda model: _delegate(runtime, "setModel", model),
        "getThinkingLevel": lambda: _delegate(runtime, "getThinkingLevel"),
        "setThinkingLevel": lambda level: _delegate(runtime, "setThinkingLevel", level),
        "registerProvider": lambda name, config: _delegate(runtime, "registerProvider", name, config, extension["path"]),
        "unregisterProvider": lambda name: _delegate(runtime, "unregisterProvider", name, extension["path"]),
        "events": event_bus,
    }
    return api


def _register_shortcut(extension: Extension, runtime: dict[str, Any], shortcut: str, options: dict[str, Any]) -> None:
    runtime["assertActive"]()
    extension.setdefault("shortcuts", {})[shortcut] = {"shortcut": shortcut, "extensionPath": extension["path"], **options}


def _register_message_renderer(extension: Extension, runtime: dict[str, Any], custom_type: str, renderer: Any) -> None:
    runtime["assertActive"]()
    extension.setdefault("messageRenderers", {})[custom_type] = renderer


def _delegate(runtime: dict[str, Any], method: str, *args: Any) -> Any:
    runtime["assertActive"]()
    return runtime[method](*args)


async def load_extension_from_factory(
    factory: Any,
    cwd: str,
    event_bus: Any,
    runtime: dict[str, Any],
    extension_path: str = "<inline>",
) -> Extension:
    """Create an Extension from an inline factory function."""
    extension = _create_extension(extension_path, extension_path)
    api = _create_extension_api(extension, runtime, cwd, event_bus)
    result = factory(api)
    if hasattr(result, "__await__"):
        await result
    return extension


async def load_extensions(
    paths: list[str],
    cwd: str,
    event_bus: Any | None = None,
) -> LoadExtensionsResult:
    """Load extensions from paths.

    In the Python port, extensions are Python modules that export a factory
    function. This loader uses importlib to load them.
    """
    import importlib.util
    import os

    extensions: list[Extension] = []
    errors: list[dict[str, str]] = []
    resolved_event_bus = event_bus or _create_event_bus()
    runtime = create_extension_runtime()

    for ext_path in paths:
        try:
            resolved_path = os.path.resolve(cwd, ext_path) if not os.path.isabs(ext_path) else ext_path
            if not os.path.exists(resolved_path):
                errors.append({"path": ext_path, "error": f"Extension not found: {ext_path}"})
                continue

            spec = importlib.util.spec_from_file_location(ext_path, resolved_path)
            if spec is None or spec.loader is None:
                errors.append({"path": ext_path, "error": f"Cannot load extension module: {ext_path}"})
                continue
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)

            factory = _resolve_extension_factory(module)
            if factory is None:
                errors.append({"path": ext_path, "error": f"Extension does not export a valid factory function: {ext_path}"})
                continue

            extension = _create_extension(ext_path, resolved_path)
            api = _create_extension_api(extension, runtime, cwd, resolved_event_bus)
            result = factory(api)
            if hasattr(result, "__await__"):
                await result
            extensions.append(extension)
        except Exception as err:
            errors.append({"path": ext_path, "error": f"Failed to load extension: {err}"})

    return LoadExtensionsResult(extensions=extensions, errors=errors, runtime=runtime)


def _resolve_extension_factory(module: Any) -> Any | None:
    candidate = getattr(module, "default", None) if hasattr(module, "default") else module
    if callable(candidate):
        return candidate
    nested = getattr(candidate, "default", None) if candidate is not None else None
    return nested if callable(nested) else None


def _create_event_bus() -> dict[str, Any]:
    """Create a minimal event bus for extension communication."""
    listeners: dict[str, list[Any]] = {}

    def on(event: str, handler: Any) -> Any:
        listeners.setdefault(event, []).append(handler)
        return lambda: listeners.get(event, []).remove(handler) if handler in listeners.get(event, []) else None

    def emit(event: str, *args: Any) -> None:
        for handler in listeners.get(event, []):
            handler(*args)

    return {"on": on, "emit": emit, "listeners": listeners}
