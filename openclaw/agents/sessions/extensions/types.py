"""Extension system types.

Extensions are modules that can subscribe to agent lifecycle events,
register LLM-callable tools, and register commands/shortcuts/flags.

This port provides the core type contracts as TypedDicts/Protocols and
the type-guard functions that have testable runtime behavior.
"""

from __future__ import annotations

from typing import Any, Literal, Protocol, TypedDict, Union


# ============================================================================
# OAuth Types
# ============================================================================

class OAuthCredentials(TypedDict, total=False):
    refresh: str
    access: str
    expires: int


class OAuthPrompt(TypedDict, total=False):
    message: str
    placeholder: str
    allowEmpty: bool


class OAuthAuthInfo(TypedDict, total=False):
    url: str
    instructions: str


class OAuthSelectOption(TypedDict):
    id: str
    label: str


class OAuthSelectPrompt(TypedDict):
    message: str
    options: list[OAuthSelectOption]


# ============================================================================
# Context Usage
# ============================================================================

class ContextUsage(TypedDict, total=False):
    tokens: int | None
    contextWindow: int
    percent: float | None


class CompactOptions(TypedDict, total=False):
    customInstructions: str
    onComplete: Any
    onError: Any


# ============================================================================
# Tool Type Guards
# ============================================================================

BUILTIN_TOOL_NAMES = frozenset({"bash", "read", "edit", "write", "grep", "find", "ls"})


def is_bash_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "bash"


def is_read_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "read"


def is_edit_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "edit"


def is_write_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "write"


def is_grep_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "grep"


def is_find_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "find"


def is_ls_tool_result(event: dict[str, Any]) -> bool:
    return event.get("toolName") == "ls"


def is_tool_call_event_type(tool_name: str, event: dict[str, Any]) -> bool:
    """Type guard for narrowing ToolCallEvent by tool name."""
    return event.get("toolName") == tool_name


# ============================================================================
# Input Event Result
# ============================================================================

InputSource = Literal["interactive", "rpc", "extension"]


def normalize_input_event_result(
    result: dict[str, Any] | None,
    original_text: str,
    original_images: list[Any] | None,
) -> dict[str, Any]:
    """Normalize an input event handler result into a standard action."""
    if result is None:
        return {"action": "continue"}
    action = result.get("action", "continue")
    if action == "handled":
        return {"action": "handled"}
    if action == "transform":
        return {
            "action": "transform",
            "text": result.get("text", original_text),
            "images": result.get("images", original_images),
        }
    return {"action": "continue"}


# ============================================================================
# Tool Definition
# ============================================================================

class ToolDefinition(TypedDict, total=False):
    name: str
    label: str
    description: str
    promptSnippet: str
    promptGuidelines: list[str]
    parameters: Any
    renderShell: Literal["default", "self"]
    executionMode: Literal["sequential", "parallel"]


def define_tool(tool: dict[str, Any]) -> dict[str, Any]:
    """Preserve parameter inference for standalone tool definitions."""
    return tool


# ============================================================================
# Provider Config
# ============================================================================

class ProviderModelConfig(TypedDict, total=False):
    id: str
    name: str
    api: str
    baseUrl: str
    reasoning: bool
    input: list[Literal["text", "image"]]
    contextWindow: int
    maxTokens: int


class ProviderConfig(TypedDict, total=False):
    name: str
    baseUrl: str
    apiKey: str
    api: str
    headers: dict[str, str]
    authHeader: bool
    models: list[ProviderModelConfig]


# ============================================================================
# Registered Items
# ============================================================================

class RegisteredTool(TypedDict, total=False):
    definition: ToolDefinition
    sourceInfo: Any


class RegisteredCommand(TypedDict, total=False):
    name: str
    sourceInfo: Any
    description: str
    handler: Any


class ExtensionFlag(TypedDict, total=False):
    name: str
    description: str
    type: Literal["boolean", "string"]
    default: bool | str
    extensionPath: str


class ExtensionShortcut(TypedDict, total=False):
    shortcut: str
    description: str
    handler: Any
    extensionPath: str


class ExtensionError(TypedDict, total=False):
    extensionPath: str
    event: str
    error: str
    stack: str


# ============================================================================
# Extension Runtime
# ============================================================================

class ExtensionRuntimeState(TypedDict, total=False):
    flagValues: dict[str, bool | str]
    pendingProviderRegistrations: list[dict[str, Any]]
    assertActive: Any
    invalidate: Any
    registerProvider: Any
    unregisterProvider: Any


class SourceInfo(TypedDict, total=False):
    source: str
    baseDir: str | None


class Extension(TypedDict, total=False):
    path: str
    resolvedPath: str
    sourceInfo: SourceInfo
    handlers: dict[str, list[Any]]
    tools: dict[str, RegisteredTool]
    messageRenderers: dict[str, Any]
    commands: dict[str, RegisteredCommand]
    flags: dict[str, ExtensionFlag]
    shortcuts: dict[str, ExtensionShortcut]


class LoadExtensionsResult(TypedDict, total=False):
    extensions: list[Extension]
    errors: list[dict[str, str]]
    runtime: Any


def create_synthetic_source_info(
    path: str,
    options: dict[str, Any] | None = None,
) -> SourceInfo:
    """Create a synthetic SourceInfo for inline or temporary extensions."""
    options = options or {}
    source = options.get("source", "local")
    base_dir = options.get("baseDir")
    return {"source": source, "baseDir": base_dir}


# ============================================================================
# Reserved Keybindings
# ============================================================================

RESERVED_KEYBINDINGS_FOR_EXTENSION_CONFLICTS = frozenset({
    "app.interrupt",
    "app.clear",
    "app.exit",
    "app.suspend",
    "app.thinking.cycle",
    "app.model.cycleForward",
    "app.model.cycleBackward",
    "app.model.select",
    "app.tools.expand",
    "app.thinking.toggle",
    "app.editor.external",
    "app.message.followUp",
    "tui.input.submit",
    "tui.select.confirm",
    "tui.select.cancel",
    "tui.input.copy",
    "tui.editor.deleteToLineEnd",
})
