"""Tests for ACP runtime modules."""

from openclaw.acp.runtime import (
    AcpRuntimeError,
    AcpSessionNotFoundError,
    AcpBackendUnavailableError,
    configure_acp_error_redactor,
    redact_sensitive_text,
    register_acp_runtime_backend,
    get_acp_runtime_backend,
    require_acp_runtime_backend,
    reset_acp_backends_for_tests,
    is_acp_enabled_by_policy,
    is_acp_runtime_spawn_available,
)


class TestAcpErrors:
    def test_base_error(self):
        err = AcpRuntimeError("something")
        assert str(err) == "something"
        assert err.code == "ACP_RUNTIME_ERROR"

    def test_session_not_found(self):
        err = AcpSessionNotFoundError("s1")
        assert "s1" in str(err)
        assert err.code == "ACP_SESSION_NOT_FOUND"

    def test_backend_unavailable(self):
        err = AcpBackendUnavailableError()
        assert "unavailable" in str(err).lower()

    def test_custom_code(self):
        err = AcpRuntimeError("msg", code="CUSTOM")
        assert err.code == "CUSTOM"


class TestRedaction:
    def test_no_redactor(self):
        assert redact_sensitive_text("hello") == "hello"

    def test_with_redactor(self):
        configure_acp_error_redactor(lambda s: s.replace("secret", "***"))
        assert redact_sensitive_text("my secret here") == "my *** here"


class TestRegistry:
    def setup_method(self):
        reset_acp_backends_for_tests()

    def test_register_and_get(self):
        backend = {"id": "local", "healthy": lambda: True}
        register_acp_runtime_backend("local", backend)
        assert get_acp_runtime_backend("local") is backend

    def test_get_nonexistent(self):
        assert get_acp_runtime_backend("nope") is None

    def test_get_default(self):
        backend = {"id": "default"}
        register_acp_runtime_backend("default", backend)
        assert get_acp_runtime_backend() is backend

    def test_require_raises(self):
        try:
            require_acp_runtime_backend("missing")
            assert False
        except AcpBackendUnavailableError:
            pass

    def test_require_returns(self):
        backend = {"id": "b1"}
        register_acp_runtime_backend("b1", backend)
        assert require_acp_runtime_backend("b1") is backend


class TestAvailability:
    def setup_method(self):
        reset_acp_backends_for_tests()

    def test_sandboxed_blocks(self):
        assert is_acp_runtime_spawn_available(sandboxed=True) is False

    def test_no_backend(self):
        assert is_acp_runtime_spawn_available() is False

    def test_with_healthy_backend(self):
        register_acp_runtime_backend("b", {"healthy": lambda: True})
        assert is_acp_runtime_spawn_available(backend_id="b") is True

    def test_with_unhealthy_backend(self):
        register_acp_runtime_backend("b", {"healthy": lambda: False})
        assert is_acp_runtime_spawn_available(backend_id="b") is False

    def test_backend_no_healthy_fn(self):
        register_acp_runtime_backend("b", {})
        assert is_acp_runtime_spawn_available(backend_id="b") is True

    def test_healthy_throws(self):
        register_acp_runtime_backend("b", {"healthy": lambda: (_ for _ in ()).throw(RuntimeError())})
        assert is_acp_runtime_spawn_available(backend_id="b") is False

    def test_policy_disabled(self):
        register_acp_runtime_backend("b", {"healthy": lambda: True})
        assert is_acp_runtime_spawn_available(config={"acp": {"enabled": False}}) is False

    def test_policy_enabled(self):
        register_acp_runtime_backend("b", {"healthy": lambda: True})
        assert is_acp_runtime_spawn_available(config={"acp": {"enabled": True}}) is True

    def test_policy_no_acp_key(self):
        register_acp_runtime_backend("b", {"healthy": lambda: True})
        assert is_acp_runtime_spawn_available(config={}) is True

    def test_backend_from_config(self):
        register_acp_runtime_backend("custom", {"healthy": lambda: True})
        assert is_acp_runtime_spawn_available(config={"acp": {"backend": "custom"}}) is True
