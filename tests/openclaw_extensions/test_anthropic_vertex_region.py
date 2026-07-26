"""Tests for Anthropic Vertex region helpers."""

from __future__ import annotations

from openclaw_extensions.anthropic_vertex.api import (
    resolve_anthropic_vertex_region,
    resolve_anthropic_vertex_region_from_base_url,
)


def test_accepts_well_formed_regional_env_values() -> None:
    assert resolve_anthropic_vertex_region({"GOOGLE_CLOUD_LOCATION": "us-east1"}) == "us-east1"


def test_falls_back_to_default_region_for_malformed_env_values() -> None:
    assert (
        resolve_anthropic_vertex_region({"GOOGLE_CLOUD_LOCATION": "us-central1.attacker.example"})
        == "global"
    )


def test_parses_regional_vertex_endpoints() -> None:
    assert (
        resolve_anthropic_vertex_region_from_base_url(
            "https://europe-west4-aiplatform.googleapis.com"
        )
        == "europe-west4"
    )


def test_treats_global_vertex_endpoint_as_global() -> None:
    assert (
        resolve_anthropic_vertex_region_from_base_url("https://aiplatform.googleapis.com")
        == "global"
    )


def test_does_not_infer_vertex_region_from_custom_proxy_hosts() -> None:
    assert (
        resolve_anthropic_vertex_region_from_base_url("https://proxy.example.com/google/aiplatform")
        is None
    )
