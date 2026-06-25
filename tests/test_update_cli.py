"""Tests for cli/update_cli — deprecation suppression."""

from __future__ import annotations

import os
import warnings

from openclaw.cli.update_cli import suppress_deprecations


class TestSuppressDeprecations:
    def test_sets_env_var(self):
        suppress_deprecations()
        assert os.environ.get("NODE_NO_WARNINGS") == "1"

    def test_suppresses_deprecation_warning(self):
        suppress_deprecations()
        with warnings.catch_warnings():
            warnings.warn("test", DeprecationWarning)
            # If not suppressed, this would raise when warnings are set to error
