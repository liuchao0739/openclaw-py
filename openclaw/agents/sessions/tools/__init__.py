"""Session tool public barrel.

Re-exports built-in tool contracts, truncation helpers, and shared utilities.
Tool factory stubs (bash, edit, read, write, find, grep, ls) are provided
with deferred implementations until the full runtime is ported.
"""

from openclaw.agents.sessions.tools.edit_diff import (
    Edit,
    EditDiffError,
    EditDiffResult,
    apply_edits_to_normalized_content,
    compute_edits_diff,
    detect_line_ending,
    generate_diff_string,
    generate_unified_patch,
    normalize_to_lf,
    restore_line_endings,
    strip_bom,
)
from openclaw.agents.sessions.tools.file_mutation_queue import with_file_mutation_queue
from openclaw.agents.sessions.tools.limits import (
    SESSION_TOOL_STDERR_TAIL_BYTES,
    append_bounded_text_tail,
    normalize_positive_limit,
)
from openclaw.agents.sessions.tools.path_utils import (
    resolve_read_path,
    resolve_to_cwd,
)
from openclaw.agents.sessions.tools.private_temp_file import (
    create_private_temp_write_stream,
)
from openclaw.agents.sessions.tools.render_utils import (
    get_text_output,
    normalize_display_text,
    replace_tabs,
    shorten_path,
    strip_ansi,
    str_value,
)
from openclaw.agents.sessions.tools.tool_contracts import (
    BashToolDetails,
    BashToolInput,
    EditToolDetails,
    EditToolInput,
    FindToolDetails,
    FindToolInput,
    GrepToolDetails,
    GrepToolInput,
    LsToolDetails,
    LsToolInput,
    ReadToolDetails,
    ReadToolInput,
    WriteToolInput,
)
from openclaw.agents.sessions.tools.tool_definition_wrapper import (
    create_tool_definition_from_agent_tool,
    wrap_tool_definition,
    wrap_tool_definitions,
)
from openclaw.agents.sessions.tools.truncate import (
    DEFAULT_MAX_BYTES,
    DEFAULT_MAX_LINES,
    GREP_MAX_LINE_LENGTH,
    TruncationOptions,
    TruncationResult,
    format_size,
    truncate_head,
    truncate_line,
    truncate_tail,
)

ToolName = str

__all__ = [
    "DEFAULT_MAX_BYTES",
    "DEFAULT_MAX_LINES",
    "Edit",
    "EditDiffError",
    "EditDiffResult",
    "EditToolDetails",
    "EditToolInput",
    "FindToolDetails",
    "FindToolInput",
    "GREP_MAX_LINE_LENGTH",
    "GrepToolDetails",
    "GrepToolInput",
    "LsToolDetails",
    "LsToolInput",
    "ReadToolDetails",
    "ReadToolInput",
    "SESSION_TOOL_STDERR_TAIL_BYTES",
    "TruncationOptions",
    "TruncationResult",
    "WriteToolInput",
    "apply_edits_to_normalized_content",
    "append_bounded_text_tail",
    "compute_edits_diff",
    "create_private_temp_write_stream",
    "create_tool_definition_from_agent_tool",
    "detect_line_ending",
    "format_size",
    "generate_diff_string",
    "generate_unified_patch",
    "get_text_output",
    "normalize_display_text",
    "normalize_positive_limit",
    "normalize_to_lf",
    "replace_tabs",
    "resolve_read_path",
    "resolve_to_cwd",
    "restore_line_endings",
    "shorten_path",
    "str_value",
    "strip_ansi",
    "strip_bom",
    "truncate_head",
    "truncate_line",
    "truncate_tail",
    "with_file_mutation_queue",
    "wrap_tool_definition",
    "wrap_tool_definitions",
]
