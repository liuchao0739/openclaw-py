"""Tests for commands/gateway-status — test support."""

from __future__ import annotations

from openclaw.commands.gateway_status import create_secret_ref_gateway_config


class TestCreateSecretRefGatewayConfig:
    def test_default(self):
        config = create_secret_ref_gateway_config()
        assert config["secrets"]["defaults"]["env"] == "default"
        assert config["gateway"]["auth"]["mode"] == "token"
        assert config["gateway"]["auth"]["token"]["id"] == "OPENCLAW_GATEWAY_TOKEN"
        assert config["gateway"]["remote"]["url"] == "wss://remote.example:18789"
        assert "mode" not in config["gateway"]  # No mode when not specified

    def test_with_local_mode(self):
        config = create_secret_ref_gateway_config("local")
        assert config["gateway"]["mode"] == "local"

    def test_with_remote_mode(self):
        config = create_secret_ref_gateway_config("remote")
        assert config["gateway"]["mode"] == "remote"

    def test_has_password_secret_refs(self):
        config = create_secret_ref_gateway_config()
        assert config["gateway"]["auth"]["password"]["id"] == "OPENCLAW_GATEWAY_PASSWORD"
        assert config["gateway"]["remote"]["password"]["id"] == "REMOTE_GATEWAY_PASSWORD"

    def test_all_secret_refs_use_env_source(self):
        config = create_secret_ref_gateway_config()
        auth = config["gateway"]["auth"]
        remote = config["gateway"]["remote"]
        for ref in [auth["token"], auth["password"], remote["token"], remote["password"]]:
            assert ref["source"] == "env"
            assert ref["provider"] == "default"
