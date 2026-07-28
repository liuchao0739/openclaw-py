from __future__ import annotations

from typing import Any, Callable

CuratedLanguageInfo: dict[str, Any] = {
    "javascript": {"id": "javascript", "name": "JavaScript", "aliases": ["js", "mjs", "cjs"]},
    "typescript": {"id": "typescript", "name": "TypeScript", "aliases": ["ts", "mts", "cts"]},
    "tsx": {"id": "tsx", "name": "TSX"},
    "jsx": {"id": "jsx", "name": "JSX"},
    "json": {"id": "json", "name": "JSON", "aliases": ["jsonc", "json5", "jsonl"]},
    "markdown": {"id": "markdown", "name": "Markdown", "aliases": ["md"]},
    "yaml": {"id": "yaml", "name": "YAML", "aliases": ["yml"]},
    "css": {"id": "css", "name": "CSS"},
    "html": {"id": "html", "name": "HTML"},
    "sh": {"id": "sh", "name": "Shell", "aliases": ["bash", "shell", "shellscript", "zsh"]},
    "python": {"id": "python", "name": "Python", "aliases": ["py"]},
    "go": {"id": "go", "name": "Go"},
    "rust": {"id": "rust", "name": "Rust", "aliases": ["rs"]},
    "java": {"id": "java", "name": "Java"},
    "c": {"id": "c", "name": "C"},
    "cpp": {"id": "cpp", "name": "C++", "aliases": ["c++"]},
    "csharp": {"id": "csharp", "name": "C#", "aliases": ["c#", "cs"]},
    "php": {"id": "php", "name": "PHP"},
    "sql": {"id": "sql", "name": "SQL"},
    "docker": {"id": "docker", "name": "Docker", "aliases": ["dockerfile"]},
    "ruby": {"id": "ruby", "name": "Ruby", "aliases": ["rb"]},
    "swift": {"id": "swift", "name": "Swift"},
    "kotlin": {"id": "kotlin", "name": "Kotlin", "aliases": ["kt", "kts"]},
    "r": {"id": "r", "name": "R"},
    "dart": {"id": "dart", "name": "Dart"},
    "lua": {"id": "lua", "name": "Lua"},
    "powershell": {"id": "powershell", "name": "PowerShell", "aliases": ["ps", "ps1"]},
    "xml": {"id": "xml", "name": "XML"},
    "toml": {"id": "toml", "name": "TOML"},
}


def get_bundled_language_aliases(language: dict[str, Any]) -> list[str]:
    return list(language.get("aliases", []))


bundled_languages_base: dict[str, Any] = {
    lang["id"]: lang for lang in CuratedLanguageInfo.values()
}

bundled_languages_alias: dict[str, str] = {}
for lang in CuratedLanguageInfo.values():
    for alias in get_bundled_language_aliases(lang):
        bundled_languages_alias[alias] = lang["id"]

bundled_languages: dict[str, Any] = {**bundled_languages_base, **bundled_languages_alias}

BASE_DIFF_VIEWER_LANGUAGE_HINTS = tuple(bundled_languages_base.keys()) + ("text", "ansi")

BASE_LANGUAGE_HINTS = set(BASE_DIFF_VIEWER_LANGUAGE_HINTS)
BASE_LANGUAGE_ALIASES: dict[str, str] = {}
for lang in CuratedLanguageInfo.values():
    for alias in get_bundled_language_aliases(lang):
        BASE_LANGUAGE_ALIASES[alias] = lang["id"]