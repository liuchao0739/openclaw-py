"""Flows package — doctor error messages and health check registry."""

from .doctor_error_message import scrub_doctor_error_message, ERR_MESSAGE_MAX_LEN
from .health_check_registry import (
    HealthCheckRegistrationError,
    register_health_check,
    list_health_checks,
    list_extension_health_checks_for_doctor,
    get_health_check,
    clear_health_checks_for_test,
)

__all__ = [
    "scrub_doctor_error_message",
    "ERR_MESSAGE_MAX_LEN",
    "HealthCheckRegistrationError",
    "register_health_check",
    "list_health_checks",
    "list_extension_health_checks_for_doctor",
    "get_health_check",
    "clear_health_checks_for_test",
]
