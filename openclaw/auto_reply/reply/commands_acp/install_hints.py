"""Builds install hints for ACP runtimes missing local prerequisites."""

from __future__ import annotations

import os
from pathlib import Path

from openclaw.config.models import OpenClawConfig
from openclaw.packages.normalization_core import (
    normalize_optional_lowercase_string,
    normalize_optional_string,
)
from openclaw.plugins.bundled_sources import resolve_bundled_plugin_install_command_hint

_INSTALL_PREFIX = "openclaw plugins install "


def resolve_acp_install_command_hint(cfg: OpenClawConfig) -> str:
    """Resolve the install command hint shown when the ACP backend is missing."""
    acp = cfg.acp
    runtime = acp.runtime if acp else None
    configured = normalize_optional_string(runtime.install_command if runtime else None)
    if configured:
        return configured

    workspace_dir = Path(os.getcwd())
    backend_id = normalize_optional_lowercase_string(acp.backend if acp else None) or "acpx"
    if backend_id != "acpx":
        return f'Install and enable the plugin that provides ACP backend "{backend_id}".'

    workspace_local_path = workspace_dir / "extensions" / "acpx"
    if workspace_local_path.exists():
        return f"{_INSTALL_PREFIX}{workspace_local_path}"

    bundled_install_hint = resolve_bundled_plugin_install_command_hint(
        plugin_id=backend_id,
        workspace_dir=workspace_dir,
    )
    if bundled_install_hint:
        local_path = bundled_install_hint.removeprefix(_INSTALL_PREFIX)
        resolved_local_path = Path(local_path).resolve()
        # Only surface local path hints that belong to the current workspace.
        if (
            _belongs_to_workspace(resolved_local_path, workspace_dir)
            and resolved_local_path.exists()
        ):
            return bundled_install_hint

    return "openclaw plugins install acpx"


def _belongs_to_workspace(candidate: Path, workspace_dir: Path) -> bool:
    try:
        candidate.relative_to(workspace_dir.resolve())
    except ValueError:
        return False
    return True
