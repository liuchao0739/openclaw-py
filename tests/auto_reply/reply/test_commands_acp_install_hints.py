"""Tests ACP install hint detection and command guidance."""

from __future__ import annotations

import os
from pathlib import Path

import pytest

from openclaw.auto_reply.reply.commands_acp.install_hints import (
    resolve_acp_install_command_hint,
)
from openclaw.config.models import OpenClawConfig


def with_acp_config(acp: dict) -> OpenClawConfig:
    return OpenClawConfig.model_validate({"acp": acp})


def test_prefers_explicit_runtime_install_command() -> None:
    cfg = with_acp_config({"runtime": {"installCommand": "pnpm openclaw plugins install acpx"}})
    assert resolve_acp_install_command_hint(cfg) == "pnpm openclaw plugins install acpx"


def test_uses_local_acpx_extension_path_when_present(tmp_path: Path, monkeypatch) -> None:
    (tmp_path / "extensions" / "acpx").mkdir(parents=True)
    monkeypatch.chdir(tmp_path)

    cfg = with_acp_config({"backend": "acpx"})
    expected = os.path.join(str(tmp_path), "extensions", "acpx")
    assert resolve_acp_install_command_hint(cfg) == f"openclaw plugins install {expected}"


def test_falls_back_to_scoped_hint_when_local_extension_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    cfg = with_acp_config({"backend": "acpx"})
    assert resolve_acp_install_command_hint(cfg) == "openclaw plugins install acpx"


def test_returns_generic_plugin_hint_for_non_acpx_backend() -> None:
    cfg = with_acp_config({"backend": "custom-backend"})
    assert resolve_acp_install_command_hint(cfg) == (
        'Install and enable the plugin that provides ACP backend "custom-backend".'
    )


def test_backend_id_is_lowercased() -> None:
    cfg = with_acp_config({"backend": "  Custom-Backend  "})
    assert resolve_acp_install_command_hint(cfg) == (
        'Install and enable the plugin that provides ACP backend "custom-backend".'
    )


def test_defaults_to_acpx_when_backend_absent(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)

    assert resolve_acp_install_command_hint(OpenClawConfig()) == "openclaw plugins install acpx"


@pytest.mark.parametrize("install_command", ["", "   "])
def test_blank_install_command_falls_through(
    install_command: str, tmp_path: Path, monkeypatch
) -> None:
    monkeypatch.chdir(tmp_path)

    cfg = with_acp_config({"runtime": {"installCommand": install_command}})
    assert resolve_acp_install_command_hint(cfg) == "openclaw plugins install acpx"
