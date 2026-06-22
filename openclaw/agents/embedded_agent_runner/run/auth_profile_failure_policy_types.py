"""Scope for classifying auth-profile failures."""

from __future__ import annotations

from typing import Literal

AuthProfileFailurePolicy = Literal["shared", "local", "local_transient"]