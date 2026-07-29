from __future__ import annotations

from typing import Any


def generate_plugin_template(name: str, output_dir: str | None = None) -> str:
    import os

    target = os.path.join(output_dir or os.getcwd(), name)
    return target


def validate_plugin_manifest(manifest: dict) -> list[str]:
    errors: list[str] = []
    if not manifest.get("name"):
        errors.append("Missing name")
    if not manifest.get("version"):
        errors.append("Missing version")
    return errors
