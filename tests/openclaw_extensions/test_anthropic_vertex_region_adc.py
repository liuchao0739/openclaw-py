"""Tests for Anthropic Vertex ADC reads."""

from __future__ import annotations

from pathlib import Path

from openclaw_extensions.anthropic_vertex.region import (
    has_anthropic_vertex_available_auth,
    resolve_anthropic_vertex_project_id,
)


def test_reads_explicit_adc_credentials_without_exists_sync_preflight(tmp_path: Path) -> None:
    adc_path = tmp_path / "vertex-adc.json"
    adc_path.write_text('{"project_id":"vertex-project"}', encoding="utf-8")
    env = {"GOOGLE_APPLICATION_CREDENTIALS": str(adc_path)}

    assert resolve_anthropic_vertex_project_id(env) == "vertex-project"
    assert has_anthropic_vertex_available_auth(env) is True


def test_respects_home_when_probing_default_adc_path(tmp_path: Path) -> None:
    home_dir = tmp_path / "vertex-home"
    home_dir.mkdir()
    default_adc_path = home_dir / ".config" / "gcloud" / "application_default_credentials.json"
    default_adc_path.parent.mkdir(parents=True)
    default_adc_path.write_text('{"project_id":"vertex-project"}', encoding="utf-8")
    env = {"HOME": str(home_dir)}

    assert resolve_anthropic_vertex_project_id(env) == "vertex-project"
    assert has_anthropic_vertex_available_auth(env) is True
