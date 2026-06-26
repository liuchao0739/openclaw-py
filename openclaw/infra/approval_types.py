"""Approval kind is shared by exec and plugin approval routing surfaces.

Mirrors src/infra/approval-types.ts.
"""

from __future__ import annotations

from typing import Literal

ChannelApprovalKind = Literal["exec", "plugin"]
