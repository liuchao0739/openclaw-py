from __future__ import annotations

from typing import Literal


FILE_TRANSFER_NODE_INVOKE_COMMANDS = [
    "file.fetch",
    "dir.list",
    "dir.fetch",
    "file.write",
]

FileTransferNodeInvokeCommand = Literal[
    "file.fetch",
    "dir.list",
    "dir.fetch",
    "file.write",
]