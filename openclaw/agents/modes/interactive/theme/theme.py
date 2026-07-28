from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass, field
from typing import Any, Callable

ColorValue = str | int

THEME_KEY = "__openclaw_agent_theme__"

CUBE_VALUES = [0, 95, 135, 175, 215, 255]
GRAY_VALUES = [8 + i * 10 for i in range(24)]

ThemeColor = str
ThemeBg = str

COLOR_MODE = "truecolor" | "256color"


def hex_to_rgb(hex_color: str) -> tuple[int, int, int]:
    cleaned = hex_color.replace("#", "")
    if len(cleaned) != 6:
        raise ValueError(f"Invalid hex color: {hex_color}")
    r = int(cleaned[0:2], 16)
    g = int(cleaned[2:4], 16)
    b = int(cleaned[4:6], 16)
    return (r, g, b)


def find_closest_cube_index(value: int) -> int:
    min_dist = float("inf")
    min_idx = 0
    for i, v in enumerate(CUBE_VALUES):
        dist = abs(value - v)
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def find_closest_gray_index(gray: int) -> int:
    min_dist = float("inf")
    min_idx = 0
    for i, v in enumerate(GRAY_VALUES):
        dist = abs(gray - v)
        if dist < min_dist:
            min_dist = dist
            min_idx = i
    return min_idx


def color_distance(r1: int, g1: int, b1: int, r2: int, g2: int, b2: int) -> float:
    dr = r1 - r2
    dg = g1 - g2
    db = b1 - b2
    return dr * dr * 0.299 + dg * dg * 0.587 + db * db * 0.114


def rgb_to_256(r: int, g: int, b: int) -> int:
    r_idx = find_closest_cube_index(r)
    g_idx = find_closest_cube_index(g)
    b_idx = find_closest_cube_index(b)
    cube_r = CUBE_VALUES[r_idx]
    cube_g = CUBE_VALUES[g_idx]
    cube_b = CUBE_VALUES[b_idx]
    cube_index = 16 + 36 * r_idx + 6 * g_idx + b_idx
    cube_dist = color_distance(r, g, b, cube_r, cube_g, cube_b)

    gray = round(0.299 * r + 0.587 * g + 0.114 * b)
    gray_idx = find_closest_gray_index(gray)
    gray_value = GRAY_VALUES[gray_idx]
    gray_index = 232 + gray_idx
    gray_dist = color_distance(r, g, b, gray_value, gray_value, gray_value)

    max_c = max(r, g, b)
    min_c = min(r, g, b)
    spread = max_c - min_c

    if spread < 10 and gray_dist < cube_dist:
        return gray_index

    return cube_index


def hex_to_256(hex_color: str) -> int:
    r, g, b = hex_to_rgb(hex_color)
    return rgb_to_256(r, g, b)


def fg_ansi(color: str | int, mode: str) -> str:
    if color == "":
        return "\x1b[39m"
    if isinstance(color, int):
        return f"\x1b[38;5;{color}m"
    if color.startswith("#"):
        if mode == "truecolor":
            r, g, b = hex_to_rgb(color)
            return f"\x1b[38;2;{r};{g};{b}m"
        idx = hex_to_256(color)
        return f"\x1b[38;5;{idx}m"
    raise ValueError(f"Invalid color value: {color}")


def bg_ansi(color: str | int, mode: str) -> str:
    if color == "":
        return "\x1b[49m"
    if isinstance(color, int):
        return f"\x1b[48;5;{color}m"
    if color.startswith("#"):
        if mode == "truecolor":
            r, g, b = hex_to_rgb(color)
            return f"\x1b[48;2;{r};{g};{b}m"
        idx = hex_to_256(color)
        return f"\x1b[48;5;{idx}m"
    raise ValueError(f"Invalid color value: {color}")


def resolve_var_refs(
    value: ColorValue,
    vars_dict: dict[str, ColorValue],
    visited: set[str] | None = None,
) -> ColorValue:
    if visited is None:
        visited = set()
    if isinstance(value, int) or value == "" or value.startswith("#"):
        return value
    if value in visited:
        raise ValueError(f"Circular variable reference detected: {value}")
    if value not in vars_dict:
        raise ValueError(f"Variable reference not found: {value}")
    visited.add(value)
    return resolve_var_refs(vars_dict[value], vars_dict, visited)


def resolve_theme_colors(
    colors: dict[str, ColorValue],
    vars_dict: dict[str, ColorValue] | None = None,
) -> dict[str, ColorValue]:
    if vars_dict is None:
        vars_dict = {}
    resolved: dict[str, ColorValue] = {}
    for key, value in colors.items():
        resolved[key] = resolve_var_refs(value, vars_dict)
    return resolved


@dataclass
class ThemeJson:
    name: str
    colors: dict[str, ColorValue]
    vars: dict[str, ColorValue] | None = None
    schema: str | None = None
    export: dict[str, ColorValue] | None = None


@dataclass
class SourceInfo:
    path: str | None = None
    line: int | None = None
    col: int | None = None


class Theme:
    def __init__(
        self,
        fg_colors: dict[str, str | int],
        bg_colors: dict[str, str | int],
        mode: str,
        name: str | None = None,
        source_path: str | None = None,
        source_info: SourceInfo | None = None,
    ):
        self.name = name
        self.source_path = source_path
        self.source_info = source_info
        self._mode = mode
        self._fg_colors: dict[str, str] = {}
        for key, value in fg_colors.items():
            self._fg_colors[key] = fg_ansi(value, mode)
        self._bg_colors: dict[str, str] = {}
        for key, value in bg_colors.items():
            self._bg_colors[key] = bg_ansi(value, mode)

    def fg(self, color: str, text: str) -> str:
        ansi = self._fg_colors.get(color)
        if ansi is None:
            raise ValueError(f"Unknown theme color: {color}")
        return f"{ansi}{text}\x1b[39m"

    def bg(self, color: str, text: str) -> str:
        ansi = self._bg_colors.get(color)
        if ansi is None:
            raise ValueError(f"Unknown theme background color: {color}")
        return f"{ansi}{text}\x1b[49m"

    def bold(self, text: str) -> str:
        return f"\x1b[1m{text}\x1b[22m"

    def italic(self, text: str) -> str:
        return f"\x1b[3m{text}\x1b[23m"

    def underline(self, text: str) -> str:
        return f"\x1b[4m{text}\x1b[24m"

    def inverse(self, text: str) -> str:
        return f"\x1b[7m{text}\x1b[27m"

    def strikethrough(self, text: str) -> str:
        return f"\x1b[9m{text}\x1b[29m"

    def get_fg_ansi(self, color: str) -> str:
        ansi = self._fg_colors.get(color)
        if ansi is None:
            raise ValueError(f"Unknown theme color: {color}")
        return ansi

    def get_bg_ansi(self, color: str) -> str:
        ansi = self._bg_colors.get(color)
        if ansi is None:
            raise ValueError(f"Unknown theme background color: {color}")
        return ansi

    def get_color_mode(self) -> str:
        return self._mode

    def get_thinking_border_color(
        self, level: str
    ) -> Callable[[str], str]:
        mapping = {
            "off": "thinkingOff",
            "minimal": "thinkingMinimal",
            "low": "thinkingLow",
            "medium": "thinkingMedium",
            "high": "thinkingHigh",
            "xhigh": "thinkingXhigh",
        }
        color_key = mapping.get(level, "thinkingOff")
        return lambda s: self.fg(color_key, s)

    def get_bash_mode_border_color(self) -> Callable[[str], str]:
        return lambda s: self.fg("bashMode", s)


BUILTIN_THEMES: dict[str, ThemeJson] | None = None
CURRENT_THEME: Theme | None = None
CURRENT_THEME_NAME: str | None = None
REGISTERED_THEMES: dict[str, Theme] = {}


def _get_themes_dir() -> str:
    return os.path.join(os.path.dirname(__file__))


def _get_custom_themes_dir() -> str:
    custom_dir = os.path.expanduser("~/.openclaw/themes")
    os.makedirs(custom_dir, exist_ok=True)
    return custom_dir


def get_builtin_themes() -> dict[str, ThemeJson]:
    global BUILTIN_THEMES
    if BUILTIN_THEMES is None:
        themes_dir = _get_themes_dir()
        dark_path = os.path.join(themes_dir, "dark.json")
        light_path = os.path.join(themes_dir, "light.json")
        with open(dark_path, "r", encoding="utf-8") as f:
            dark_data = json.load(f)
        with open(light_path, "r", encoding="utf-8") as f:
            light_data = json.load(f)
        BUILTIN_THEMES = {
            "dark": _parse_theme_json("dark", dark_data),
            "light": _parse_theme_json("light", light_data),
        }
    return BUILTIN_THEMES


def _parse_theme_json(label: str, data: dict[str, Any]) -> ThemeJson:
    if not isinstance(data, dict):
        raise ValueError(f"Theme '{label}' is not a valid JSON object")
    if "name" not in data:
        raise ValueError(f"Theme '{label}' is missing required 'name' field")
    if "colors" not in data:
        raise ValueError(f"Theme '{label}' is missing required 'colors' field")

    colors = data["colors"]
    if not isinstance(colors, dict):
        raise ValueError(f"Theme '{label}' has invalid 'colors' field")

    required_colors = [
        "accent", "border", "borderAccent", "borderMuted",
        "success", "error", "warning", "muted", "dim", "text",
        "thinkingText", "userMessageText", "customMessageText",
        "customMessageLabel", "toolTitle", "toolOutput",
        "mdHeading", "mdLink", "mdLinkUrl", "mdCode", "mdCodeBlock",
        "mdCodeBlockBorder", "mdQuote", "mdQuoteBorder", "mdHr",
        "mdListBullet", "toolDiffAdded", "toolDiffRemoved",
        "toolDiffContext", "syntaxComment", "syntaxKeyword",
        "syntaxFunction", "syntaxVariable", "syntaxString",
        "syntaxNumber", "syntaxType", "syntaxOperator",
        "syntaxPunctuation", "thinkingOff", "thinkingMinimal",
        "thinkingLow", "thinkingMedium", "thinkingHigh",
        "thinkingXhigh", "bashMode",
    ]
    missing = [c for c in required_colors if c not in colors]
    if missing:
        msg = f"Theme '{label}' is missing required color tokens:\n"
        msg += "\n".join(f"  - {c}" for c in sorted(missing))
        msg += '\n\nPlease add these colors to your theme\'s "colors" object.'
        msg += "\nSee the built-in themes (dark.json, light.json) for reference values."
        raise ValueError(msg)

    return ThemeJson(
        name=data["name"],
        colors=colors,
        vars=data.get("vars"),
        schema=data.get("$schema"),
        export=data.get("export"),
    )


def _parse_theme_json_content(label: str, content: str) -> ThemeJson:
    try:
        data = json.loads(content)
    except json.JSONDecodeError as e:
        raise ValueError(f"Failed to parse theme {label}: {e}") from e
    return _parse_theme_json(label, data)


def load_theme_json(name: str) -> ThemeJson:
    builtin = get_builtin_themes()
    if name in builtin:
        return builtin[name]
    if name in REGISTERED_THEMES:
        raise ValueError(f"Theme '{name}' is already registered as a runtime theme")
    custom_dir = _get_custom_themes_dir()
    theme_path = os.path.join(custom_dir, f"{name}.json")
    if not os.path.exists(theme_path):
        raise ValueError(f"Theme not found: {name}")
    with open(theme_path, "r", encoding="utf-8") as f:
        content = f.read()
    return _parse_theme_json_content(name, content)


def create_theme(theme_json: ThemeJson, mode: str | None = None, source_path: str | None = None) -> Theme:
    color_mode = mode or "truecolor"
    resolved = resolve_theme_colors(theme_json.colors, theme_json.vars)
    bg_color_keys = {
        "selectedBg", "userMessageBg", "customMessageBg",
        "toolPendingBg", "toolSuccessBg", "toolErrorBg",
    }
    fg_colors: dict[str, str | int] = {}
    bg_colors: dict[str, str | int] = {}
    for key, value in resolved.items():
        if key in bg_color_keys:
            bg_colors[key] = value
        else:
            fg_colors[key] = value
    return Theme(fg_colors, bg_colors, color_mode, name=theme_json.name, source_path=source_path)


def load_theme_from_path(theme_path: str, mode: str | None = None) -> Theme:
    with open(theme_path, "r", encoding="utf-8") as f:
        content = f.read()
    theme_json = _parse_theme_json_content(theme_path, content)
    return create_theme(theme_json, mode, theme_path)


def load_theme(name: str, mode: str | None = None) -> Theme:
    if name in REGISTERED_THEMES:
        return REGISTERED_THEMES[name]
    theme_json = load_theme_json(name)
    return create_theme(theme_json, mode)


class _ThemeProxy:
    def __getattr__(self, prop: str) -> Any:
        if CURRENT_THEME is None:
            raise RuntimeError("Theme not initialized. Call set_theme() first.")
        return getattr(CURRENT_THEME, prop)


theme: Theme = _ThemeProxy()  # type: ignore[assignment]


def set_theme(name: str, enable_watcher: bool = False) -> dict[str, Any]:
    global CURRENT_THEME, CURRENT_THEME_NAME
    CURRENT_THEME_NAME = name
    try:
        CURRENT_THEME = load_theme(name)
        return {"success": True}
    except Exception as e:
        CURRENT_THEME_NAME = "dark"
        CURRENT_THEME = load_theme("dark")
        return {"success": False, "error": str(e)}


def stop_theme_watcher() -> None:
    pass


def _build_cli_highlight_theme(t: Theme) -> dict[str, Callable[[str], str]]:
    return {
        "keyword": lambda s: t.fg("syntaxKeyword", s),
        "built_in": lambda s: t.fg("syntaxType", s),
        "literal": lambda s: t.fg("syntaxNumber", s),
        "number": lambda s: t.fg("syntaxNumber", s),
        "string": lambda s: t.fg("syntaxString", s),
        "comment": lambda s: t.fg("syntaxComment", s),
        "function": lambda s: t.fg("syntaxFunction", s),
        "title": lambda s: t.fg("syntaxFunction", s),
        "class": lambda s: t.fg("syntaxType", s),
        "type": lambda s: t.fg("syntaxType", s),
        "attr": lambda s: t.fg("syntaxVariable", s),
        "variable": lambda s: t.fg("syntaxVariable", s),
        "params": lambda s: t.fg("syntaxVariable", s),
        "operator": lambda s: t.fg("syntaxOperator", s),
        "punctuation": lambda s: t.fg("syntaxPunctuation", s),
    }


_CACHED_HIGHLIGHT_THEME_FOR: Theme | None = None
_CACHED_CLI_HIGHLIGHT_THEME: dict[str, Callable[[str], str]] | None = None


def get_cli_highlight_theme(t: Theme) -> dict[str, Callable[[str], str]]:
    global _CACHED_HIGHLIGHT_THEME_FOR, _CACHED_CLI_HIGHLIGHT_THEME
    if _CACHED_HIGHLIGHT_THEME_FOR is not t or _CACHED_CLI_HIGHLIGHT_THEME is None:
        _CACHED_HIGHLIGHT_THEME_FOR = t
        _CACHED_CLI_HIGHLIGHT_THEME = _build_cli_highlight_theme(t)
    return _CACHED_CLI_HIGHLIGHT_THEME


EXT_TO_LANG: dict[str, str] = {
    "ts": "typescript", "tsx": "typescript",
    "js": "javascript", "jsx": "javascript",
    "mjs": "javascript", "cjs": "javascript",
    "py": "python", "rb": "ruby",
    "rs": "rust", "go": "go",
    "java": "java", "kt": "kotlin",
    "swift": "swift", "c": "c",
    "h": "c", "cpp": "cpp",
    "cc": "cpp", "cxx": "cpp",
    "hpp": "cpp", "cs": "csharp",
    "php": "php", "sh": "bash",
    "bash": "bash", "zsh": "bash",
    "fish": "fish", "ps1": "powershell",
    "sql": "sql", "html": "html",
    "htm": "html", "css": "css",
    "scss": "scss", "sass": "sass",
    "less": "less", "json": "json",
    "yaml": "yaml", "yml": "yaml",
    "toml": "toml", "xml": "xml",
    "md": "markdown", "markdown": "markdown",
    "dockerfile": "dockerfile", "makefile": "makefile",
    "cmake": "cmake", "lua": "lua",
    "perl": "perl", "r": "r",
    "scala": "scala", "clj": "clojure",
    "ex": "elixir", "exs": "elixir",
    "erl": "erlang", "hs": "haskell",
    "ml": "ocaml", "vim": "vim",
    "graphql": "graphql", "proto": "protobuf",
    "tf": "hcl", "hcl": "hcl",
}


def get_language_from_path(file_path: str) -> str | None:
    ext = file_path.rsplit(".", 1)[-1].lower() if "." in file_path else ""
    if not ext:
        return None
    return EXT_TO_LANG.get(ext)
