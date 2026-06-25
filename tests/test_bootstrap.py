"""Tests for bootstrap — CA certificate and startup environment resolution."""

from __future__ import annotations

import pytest

from openclaw.bootstrap.node_extra_ca_certs import (
    is_node_version_manager_runtime,
    resolve_auto_node_extra_ca_certs,
    resolve_linux_system_ca_bundle,
)
from openclaw.bootstrap.node_startup_env import resolve_node_startup_tls_environment


def _allow_only(path: str):
    def _check(candidate: str) -> None:
        if candidate != path:
            raise FileNotFoundError(candidate)
    return _check


class TestResolveLinuxSystemCaBundle:
    def test_non_linux_returns_none(self):
        assert resolve_linux_system_ca_bundle("darwin") is None

    def test_linux_returns_first_readable(self):
        result = resolve_linux_system_ca_bundle("linux", _allow_only("/etc/pki/tls/certs/ca-bundle.crt"))
        assert result == "/etc/pki/tls/certs/ca-bundle.crt"

    def test_linux_no_readable_returns_none(self):
        def deny_all(_path: str) -> None:
            raise FileNotFoundError()
        assert resolve_linux_system_ca_bundle("linux", deny_all) is None


class TestIsNodeVersionManagerRuntime:
    def test_nvm_via_env(self):
        assert is_node_version_manager_runtime({"NVM_DIR": "/home/test/.nvm"}, "/usr/bin/node") is True

    def test_nvm_via_execpath(self):
        assert is_node_version_manager_runtime({}, "/home/test/.nvm/versions/node/v22/bin/node") is True

    def test_non_nvm(self):
        assert is_node_version_manager_runtime({}, "/usr/bin/node") is False

    def test_fnm_via_execpath(self):
        assert is_node_version_manager_runtime({}, "/home/test/.fnm/node-versions/v22/bin/node") is True

    def test_volta_via_execpath(self):
        assert is_node_version_manager_runtime({}, "/home/test/.volta/tools/image/node/22/bin/node") is True

    def test_asdf_via_execpath(self):
        assert is_node_version_manager_runtime({}, "/home/test/.asdf/installs/node/22/bin/node") is True

    def test_nvs_via_execpath(self):
        assert is_node_version_manager_runtime({}, "/home/test/.nvs/node/22/bin/node") is True


class TestResolveAutoNodeExtraCaCerts:
    def test_existing_env_returns_none(self):
        result = resolve_auto_node_extra_ca_certs(
            {"NODE_EXTRA_CA_CERTS": "/custom/ca.pem"},
            "linux",
            "/home/test/.nvm/bin/node",
        )
        assert result is None

    def test_non_linux_returns_none(self):
        result = resolve_auto_node_extra_ca_certs({}, "darwin", "/usr/bin/node")
        assert result is None

    def test_non_version_manager_returns_none(self):
        result = resolve_auto_node_extra_ca_certs({}, "linux", "/usr/bin/node")
        assert result is None

    def test_version_manager_linux_returns_ca_bundle(self):
        result = resolve_auto_node_extra_ca_certs(
            {"NVM_DIR": "/home/test/.nvm"},
            "linux",
            "/usr/bin/node",
            _allow_only("/etc/ssl/certs/ca-certificates.crt"),
        )
        assert result == "/etc/ssl/certs/ca-certificates.crt"


class TestResolveNodeStartupTlsEnvironment:
    def test_darwin_defaults(self):
        result = resolve_node_startup_tls_environment({}, "darwin")
        assert result["NODE_EXTRA_CA_CERTS"] == "/etc/ssl/cert.pem"
        assert result["NODE_USE_SYSTEM_CA"] == "1"

    def test_darwin_skip_defaults(self):
        result = resolve_node_startup_tls_environment({}, "darwin", include_darwin_defaults=False)
        assert result["NODE_EXTRA_CA_CERTS"] is None
        assert result["NODE_USE_SYSTEM_CA"] is None

    def test_existing_env_preserved(self):
        result = resolve_node_startup_tls_environment(
            {"NODE_EXTRA_CA_CERTS": "/custom/ca.pem", "NODE_USE_SYSTEM_CA": "0"},
            "darwin",
        )
        assert result["NODE_EXTRA_CA_CERTS"] == "/custom/ca.pem"
        assert result["NODE_USE_SYSTEM_CA"] == "0"

    def test_linux_version_manager(self):
        result = resolve_node_startup_tls_environment(
            {"NVM_DIR": "/home/test/.nvm"},
            "linux",
            "/usr/bin/node",
            access_sync=_allow_only("/etc/pki/tls/certs/ca-bundle.crt"),
        )
        assert result["NODE_EXTRA_CA_CERTS"] == "/etc/pki/tls/certs/ca-bundle.crt"
        assert result["NODE_USE_SYSTEM_CA"] is None
