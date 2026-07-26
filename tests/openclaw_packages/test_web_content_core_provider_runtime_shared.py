"""Tests for web content provider runtime shared helpers."""

from __future__ import annotations

from openclaw_packages.web_content_core import (
    has_web_provider_entry_credential,
    read_web_provider_env_value,
    resolve_web_provider_config,
    resolve_web_provider_definition,
)


def test_resolve_web_provider_config_selects_the_requested_web_tool_config() -> None:
    search = {"provider": "search-provider"}

    assert (
        resolve_web_provider_config(
            {
                "tools": {
                    "web": {
                        "search": search,
                    },
                },
            },
            "search",
        )
        == search
    )


def test_read_web_provider_env_value_normalizes_env_credentials_before_returning_them() -> None:
    assert read_web_provider_env_value(["API_KEY"], {"API_KEY": " key\r\nvalue🙂 "}) == "keyvalue"


def test_has_web_provider_entry_credential_treats_non_env_secret_refs_as_configured() -> None:
    provider = {
        "id": "custom",
        "env_vars": ["CUSTOM_API_KEY"],
    }

    assert has_web_provider_entry_credential(
        provider=provider,
        config={},
        tool_config=None,
        resolve_raw_value=lambda **_kwargs: {
            "source": "file",
            "provider": "mounted-json",
            "id": "/custom/apiKey",
        },
        resolve_env_value=lambda **_kwargs: None,
    )


def test_has_web_provider_entry_credential_resolves_env_secret_ref_ids() -> None:
    provider = {
        "id": "custom",
        "env_vars": ["CUSTOM_API_KEY"],
    }

    assert has_web_provider_entry_credential(
        provider=provider,
        config={},
        tool_config=None,
        resolve_raw_value=lambda **_kwargs: {
            "source": "env",
            "provider": "default",
            "id": "CUSTOM_API_KEY",
        },
        resolve_env_value=lambda **kwargs: (
            "secret" if kwargs.get("configured_env_var_id") == "CUSTOM_API_KEY" else None
        ),
    )


def test_has_web_provider_entry_credential_falls_back_to_provider_auth_before_env_probing() -> None:
    provider = {
        "id": "custom",
        "env_vars": ["CUSTOM_API_KEY"],
        "auth_provider_id": "custom-auth",
    }

    assert has_web_provider_entry_credential(
        provider=provider,
        config={},
        tool_config=None,
        resolve_raw_value=lambda **_kwargs: None,
        resolve_env_value=lambda **_kwargs: None,
        resolve_provider_auth_value=lambda provider_id: provider_id == "custom-auth",
    )


def test_resolve_web_provider_definition_falls_back_to_auto_detect_without_selected_provider() -> (
    None
):
    resolved = resolve_web_provider_definition(
        config={},
        tool_config={"enabled": True},
        runtime_metadata={},
        providers=[
            {
                "id": "custom",
            },
        ],
        resolve_enabled=lambda **_kwargs: True,
        resolve_auto_provider_id=lambda **_kwargs: "custom",
        create_tool=lambda *, provider, **_kwargs: {
            "name": provider["id"],
        },
    )

    assert resolved == {
        "provider": {
            "id": "custom",
        },
        "definition": {
            "name": "custom",
        },
    }
