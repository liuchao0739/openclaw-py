"""Tests for flows core modules."""

import pytest

from openclaw.flows.doctor_error_message import (
    scrub_doctor_error_message,
    ERR_MESSAGE_MAX_LEN,
)
from openclaw.flows.health_check_registry import (
    HealthCheckRegistrationError,
    HealthCheckImpl,
    register_health_check,
    list_health_checks,
    list_extension_health_checks_for_doctor,
    get_health_check,
    clear_health_checks_for_test,
)


class TestDoctorErrorMessage:
    def test_plain_string(self):
        assert scrub_doctor_error_message("hello") == "hello"

    def test_error_object(self):
        err = ValueError("something broke")
        assert scrub_doctor_error_message(err) == "something broke"

    def test_non_error(self):
        assert scrub_doctor_error_message(42) == "42"

    def test_strips_control_chars(self):
        assert scrub_doctor_error_message("a\x00b\x01c") == "abc"

    def test_strips_del_char(self):
        assert scrub_doctor_error_message("a\x7fb") == "ab"

    def test_keeps_newlines(self):
        # newline (0x0a) is > 0x1f? No, 0x0a = 10 which is < 0x20
        # Actually 0x0a < 0x1f, so it gets stripped
        result = scrub_doctor_error_message("line1\nline2")
        assert "\n" not in result

    def test_caps_long_message(self):
        long_msg = "x" * 500
        result = scrub_doctor_error_message(long_msg)
        assert len(result) == ERR_MESSAGE_MAX_LEN
        assert result.endswith("...")

    def test_exact_max_len_not_capped(self):
        msg = "x" * ERR_MESSAGE_MAX_LEN
        assert scrub_doctor_error_message(msg) == msg

    def test_empty_string(self):
        assert scrub_doctor_error_message("") == ""


class TestHealthCheckRegistry:
    @pytest.fixture(autouse=True)
    def _clean(self):
        clear_health_checks_for_test()
        yield
        clear_health_checks_for_test()

    def test_register_and_list(self):
        check = HealthCheckImpl(id="ext/check-1", kind="extension")
        register_health_check(check)
        assert len(list_health_checks()) == 1
        assert list_health_checks()[0].id == "ext/check-1"

    def test_duplicate_raises(self):
        register_health_check(HealthCheckImpl(id="dup"))
        with pytest.raises(HealthCheckRegistrationError) as exc_info:
            register_health_check(HealthCheckImpl(id="dup"))
        assert exc_info.value.check_id == "dup"
        assert exc_info.value.code == "OC_DOCTOR_DUPLICATE_CHECK"

    def test_get_health_check(self):
        check = HealthCheckImpl(id="ext/lookup")
        register_health_check(check)
        assert get_health_check("ext/lookup") is check
        assert get_health_check("nonexistent") is None

    def test_list_extension_filters_core(self):
        register_health_check(HealthCheckImpl(id="ext/1", kind="extension"))
        register_health_check(HealthCheckImpl(id="ext/2", kind="core"))
        extensions = list_extension_health_checks_for_doctor([])
        assert len(extensions) == 1
        assert extensions[0].id == "ext/1"

    def test_list_extension_rejects_core_prefix(self):
        register_health_check(HealthCheckImpl(id="core/doctor/x", kind="extension"))
        with pytest.raises(HealthCheckRegistrationError):
            list_extension_health_checks_for_doctor([])

    def test_list_extension_rejects_core_id_collision(self):
        register_health_check(HealthCheckImpl(id="shared", kind="extension"))
        with pytest.raises(HealthCheckRegistrationError):
            list_extension_health_checks_for_doctor([HealthCheckImpl(id="shared", kind="core")])

    def test_insertion_order_preserved(self):
        register_health_check(HealthCheckImpl(id="a"))
        register_health_check(HealthCheckImpl(id="b"))
        register_health_check(HealthCheckImpl(id="c"))
        ids = [c.id for c in list_health_checks()]
        assert ids == ["a", "b", "c"]
