"""Shared extraction helpers for reading the TypeScript source tree.

Regex-based rather than AST-based: the goal is a fidelity signal across ~450
modules, not a compiler. Symbol names are matched loosely (camelCase mapped to
snake_case, plus the raw name) so renames during porting still count.
"""

from __future__ import annotations

import os
import re
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_TS_REPO = "/Users/liuchao/openclaw-ts"

_EXPORT_FUNCTION = re.compile(r"^export\s+(?:async\s+)?function\s+(\w+)", re.MULTILINE)
_EXPORT_CLASS = re.compile(r"^export\s+(?:abstract\s+)?class\s+(\w+)", re.MULTILINE)
_EXPORT_ARROW = re.compile(
    r"^export\s+const\s+(\w+)\s*(?::[^=]+)?=\s*(?:async\s*)?\(", re.MULTILINE
)
_EXPORT_CONST = re.compile(r"^export\s+const\s+(\w+)\s*[:=]", re.MULTILINE)
_IMPORT_FROM = re.compile(
    r"""^\s*(?:import|export)\b[^;]*?\bfrom\s+["']([^"']+)["']""", re.MULTILINE
)
_BARE_IMPORT = re.compile(r"""^\s*import\s+["']([^"']+)["']""", re.MULTILINE)

_CAMEL_BOUNDARY = re.compile(r"(?<!^)(?=[A-Z])")


def ts_repo() -> Path:
    return Path(os.environ.get("OPENCLAW_TS_REPO", DEFAULT_TS_REPO))


def camel_to_snake(name: str) -> str:
    return _CAMEL_BOUNDARY.sub("_", name).lower()


def is_source_file(path: Path) -> bool:
    name = path.name
    if not name.endswith((".ts", ".tsx")):
        return False
    return not name.endswith((".test.ts", ".test.tsx", ".d.ts"))


@dataclass
class ModuleFacts:
    """Exported runtime API and import edges for one TypeScript directory."""

    functions: set[str] = field(default_factory=set)
    classes: set[str] = field(default_factory=set)
    constants: set[str] = field(default_factory=set)
    imports: set[str] = field(default_factory=set)
    source_lines: int = 0
    test_lines: int = 0
    file_count: int = 0

    @property
    def api(self) -> set[str]:
        return self.functions | self.classes | self.constants


def has_direct_sources(directory: Path) -> bool:
    return any(entry.is_file() and is_source_file(entry) for entry in directory.iterdir())


def read_module(directory: Path, recursive: bool = False) -> ModuleFacts:
    """Collect exported symbols and raw import specifiers for a directory.

    Workspace packages keep their code under `src/` with no sub-tasks of their
    own, so those are read recursively from that subdirectory instead.
    """
    facts = ModuleFacts()
    if not directory.is_dir():
        return facts

    package_src = directory / "src"
    if not recursive and not has_direct_sources(directory) and package_src.is_dir():
        directory = package_src
        recursive = True

    entries = sorted(directory.rglob("*") if recursive else directory.iterdir())
    for entry in entries:
        if not entry.is_file() or not entry.name.endswith((".ts", ".tsx")):
            continue
        try:
            text = entry.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        line_count = text.count("\n") + 1
        if not is_source_file(entry):
            facts.test_lines += line_count
            continue

        facts.file_count += 1
        facts.source_lines += line_count
        facts.functions |= set(_EXPORT_FUNCTION.findall(text))
        facts.classes |= set(_EXPORT_CLASS.findall(text))
        arrows = set(_EXPORT_ARROW.findall(text))
        facts.functions |= arrows
        facts.constants |= set(_EXPORT_CONST.findall(text)) - arrows
        facts.imports |= set(_IMPORT_FROM.findall(text))
        facts.imports |= set(_BARE_IMPORT.findall(text))

    return facts


_PY_DEF = re.compile(r"^\s*def\s+(\w+)", re.MULTILINE)
_PY_ASYNC_DEF = re.compile(r"^\s*async\s+def\s+(\w+)", re.MULTILINE)
_PY_CLASS = re.compile(r"^\s*class\s+(\w+)", re.MULTILINE)
_PY_ASSIGN = re.compile(r"^(\w+)\s*[:=]", re.MULTILINE)


def read_python_symbols(target: Path) -> set[str]:
    """Collect every callable/class/constant name defined under a Python target."""
    if not target.exists():
        return set()

    files: list[Path]
    if target.is_dir():
        files = sorted(target.rglob("*.py"))
    elif target.suffix == ".py":
        files = [target]
    else:
        files = sorted(target.parent.glob("*.py"))

    names: set[str] = set()
    for file in files:
        if "__pycache__" in file.parts:
            continue
        try:
            text = file.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        names |= set(_PY_DEF.findall(text))
        names |= set(_PY_ASYNC_DEF.findall(text))
        names |= set(_PY_CLASS.findall(text))
        names |= set(_PY_ASSIGN.findall(text))
    return names


def python_line_count(target: Path) -> int:
    if not target.exists():
        return 0
    files = (
        sorted(target.rglob("*.py"))
        if target.is_dir()
        else [target]
        if target.suffix == ".py"
        else []
    )
    total = 0
    for file in files:
        if "__pycache__" in file.parts:
            continue
        try:
            total += file.read_text(encoding="utf-8", errors="ignore").count("\n") + 1
        except OSError:
            continue
    return total


def match_symbols(ts_api: set[str], py_names: set[str]) -> tuple[set[str], set[str]]:
    """Split a TypeScript API into (ported, missing) by loose name matching."""
    ported = {name for name in ts_api if name in py_names or camel_to_snake(name) in py_names}
    return ported, ts_api - ported
