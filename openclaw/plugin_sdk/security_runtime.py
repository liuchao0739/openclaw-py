"""Security helpers exposed through the plugin SDK security runtime barrel.

Mirrors src/plugin-sdk/security-runtime.ts (``redactSensitiveText`` export).
"""

from __future__ import annotations

from openclaw.acp.runtime import redact_sensitive_text

__all__ = ["redact_sensitive_text"]
