from __future__ import annotations

from typing import Any

FILE_TRANSFER_SUBDIR = "file-transfer"

FILE_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024
FILE_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
DIR_LIST_DEFAULT_MAX_ENTRIES = 200
DIR_LIST_HARD_MAX_ENTRIES = 5000
DIR_FETCH_DEFAULT_MAX_BYTES = 8 * 1024 * 1024
DIR_FETCH_HARD_MAX_BYTES = 16 * 1024 * 1024
FILE_WRITE_HARD_MAX_BYTES = 16 * 1024 * 1024

_PAIRED_NODE_DESCRIPTION = (
    "Existing paired node id, display name, or IP shown by nodes status. "
    "Do not use local, host, gateway, or auto; use local file/exec tools for local workspace paths."
)

FILE_FETCH_TOOL_DESCRIPTOR: dict[str, Any] = {
    "label": "File Fetch",
    "name": "file_fetch",
    "description": (
        "Retrieve a file from a paired node by absolute path. Returns image content blocks for image MIME types, "
        "inlines small text files (≤8 KB) as text content, and saves everything else under the gateway media store "
        "with a path you can pass to file_write or other tools. Use this for screenshots, photos, receipts, logs, "
        "source files. Pair with file_write to copy a file from one node to another (no exec/cp shell-out needed). "
        "Requires operator opt-in: gateway.nodes.allowCommands must include 'file.fetch' AND "
        "plugins.entries.file-transfer.config.nodes.<node>.allowReadPaths must match the path. "
        "Without policy configured, every call is denied."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "node": {"type": "string", "description": _PAIRED_NODE_DESCRIPTION},
            "path": {
                "type": "string",
                "description": "Absolute path to the file on the node. Canonicalized server-side.",
            },
            "maxBytes": {
                "type": "integer",
                "description": "Max bytes to fetch. Default 8 MB, hard ceiling 16 MB (single round-trip).",
            },
            "gatewayUrl": {"type": "string"},
            "gatewayToken": {"type": "string"},
            "timeoutMs": {"type": "integer"},
        },
        "required": ["node", "path"],
    },
}

DIR_LIST_TOOL_DESCRIPTOR: dict[str, Any] = {
    "label": "Directory List",
    "name": "dir_list",
    "description": (
        "Retrieve a structured directory listing from a paired node, not the local workspace. "
        "Returns file and subdirectory metadata (name, path, size, mimeType, isDir, mtime) without transferring "
        "file content. Use this to discover what files exist before fetching them with file_fetch. "
        "Pagination is offset-based; pass nextPageToken from the previous result. "
        "Requires operator opt-in: gateway.nodes.allowCommands must include 'dir.list' AND "
        "plugins.entries.file-transfer.config.nodes.<node>.allowReadPaths must match the directory path. "
        "Without policy configured, every call is denied."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "node": {"type": "string", "description": _PAIRED_NODE_DESCRIPTION},
            "path": {
                "type": "string",
                "description": "Absolute path to the directory on the node. Canonicalized server-side.",
            },
            "pageToken": {
                "type": "string",
                "description": "Pagination token from a previous dir_list call. Omit to start from the beginning.",
            },
            "maxEntries": {
                "type": "integer",
                "description": f"Max entries per page. Default {DIR_LIST_DEFAULT_MAX_ENTRIES}, hard ceiling {DIR_LIST_HARD_MAX_ENTRIES}.",
            },
            "gatewayUrl": {"type": "string"},
            "gatewayToken": {"type": "string"},
            "timeoutMs": {"type": "integer"},
        },
        "required": ["node", "path"],
    },
}

DIR_FETCH_TOOL_DESCRIPTOR: dict[str, Any] = {
    "label": "Directory Fetch",
    "name": "dir_fetch",
    "description": (
        "Retrieve a directory tree from a paired node as a gzipped tarball, unpack it on the gateway, "
        "and return a manifest of saved paths. Use to pull source trees, asset folders, or log directories "
        "in a single round-trip. The unpacked files live on the GATEWAY (not your local machine); "
        "pass localPath into other tools or use file_fetch on individual entries to ship them elsewhere. "
        "Rejects trees larger than 16 MB compressed. "
        "Requires operator opt-in: gateway.nodes.allowCommands must include 'dir.fetch' AND "
        "plugins.entries.file-transfer.config.nodes.<node>.allowReadPaths must match the directory path."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "node": {"type": "string", "description": _PAIRED_NODE_DESCRIPTION},
            "path": {
                "type": "string",
                "description": "Absolute path to the directory on the node to fetch. Canonicalized server-side.",
            },
            "maxBytes": {
                "type": "integer",
                "description": "Max gzipped tarball bytes to fetch. Default 8 MB, hard ceiling 16 MB (single round-trip).",
            },
            "includeDotfiles": {
                "type": "boolean",
                "description": "Reserved for v2; currently always includes dotfiles (v1 quirk in BSD tar).",
            },
            "gatewayUrl": {"type": "string"},
            "gatewayToken": {"type": "string"},
            "timeoutMs": {"type": "integer"},
        },
        "required": ["node", "path"],
    },
}

FILE_WRITE_TOOL_DESCRIPTOR: dict[str, Any] = {
    "label": "File Write",
    "name": "file_write",
    "description": (
        "Write file bytes to a paired node by absolute path. Atomic write (temp + rename). "
        "Refuses to overwrite by default — pass overwrite=true to replace. "
        "Refuses to write through symlink targets unless policy explicitly allows following symlinks. "
        "Pair with file_fetch by passing its mediaId as sourceMediaId for binary copy. "
        "Requires operator opt-in: gateway.nodes.allowCommands must include 'file.write' AND "
        "plugins.entries.file-transfer.config.nodes.<node>.allowWritePaths must match the destination path. "
        "Without policy configured, every call is denied."
    ),
    "parameters": {
        "type": "object",
        "properties": {
            "node": {"type": "string", "description": _PAIRED_NODE_DESCRIPTION},
            "path": {
                "type": "string",
                "description": "Absolute path on the node to write. Canonicalized server-side.",
            },
            "contentBase64": {
                "type": "string",
                "description": "Base64-encoded bytes to write. Maximum 16 MB after decode.",
            },
            "sourceMediaId": {
                "type": "string",
                "description": "Media id returned by file_fetch. Preferred for binary copies.",
            },
            "mimeType": {
                "type": "string",
                "description": "Content type hint. Not validated against the content.",
            },
            "overwrite": {
                "type": "boolean",
                "description": "Allow overwriting an existing file. Default false.",
                "default": False,
            },
            "createParents": {
                "type": "boolean",
                "description": "Create missing parent directories (mkdir -p). Default false.",
                "default": False,
            },
        },
        "required": ["node", "path"],
    },
}