from __future__ import annotations

from typing import Optional

from .config_utils import parse_duration_ms
from .error_utils import format_error_message
from .fs_utils import (
    assert_no_symlink_parents,
    is_file_missing_error,
    is_path_inside,
    is_path_inside_with_realpath,
    read_regular_file,
    stat_regular_file,
)
from .internal import is_memory_path, normalize_extra_memory_paths
from .read_file_shared import (
    DEFAULT_MEMORY_READ_LINES,
    build_memory_read_result,
)
from .read_retry import retry_transient_memory_read


async def _is_allowed_additional_directory_path(additional_path: str, abs_path: str) -> bool:
    if not is_path_inside(additional_path, abs_path):
        return False
    try:
        await assert_no_symlink_parents(additional_path, abs_path)
    except Exception:
        return False
    if not is_path_inside_with_realpath(additional_path, abs_path):
        try:
            import os
            await os.lstat(abs_path)
        except Exception as err:
            return is_file_missing_error(err)
        return False
    return True


def _is_file_disappeared_during_read_error(err: object) -> bool:
    if is_file_missing_error(err):
        return True
    return bool(
        err
        and isinstance(err, dict)
        and "code" in err
        and err.get("code") == "path-mismatch"
    )


async def read_memory_file(
    workspace_dir: str,
    rel_path: str,
    extra_paths: Optional[list] = None,
    from_line: Optional[int] = None,
    lines: Optional[int] = None,
    default_lines: Optional[int] = None,
    max_chars: Optional[int] = None,
) -> dict:
    import os

    raw_path = rel_path.strip()
    if not raw_path:
        raise ValueError("path required")

    if os.path.isabs(raw_path):
        abs_path = raw_path
    else:
        abs_path = os.path.abspath(os.path.join(workspace_dir, raw_path))

    rel = os.path.relpath(abs_path, workspace_dir).replace("\\", "/")
    in_workspace = len(rel) > 0 and not rel.startswith("..") and not os.path.isabs(rel)
    allowed_workspace = in_workspace and is_memory_path(rel)
    allowed_additional = False

    if not allowed_workspace and extra_paths and len(extra_paths) > 0:
        additional_paths = normalize_extra_memory_paths(workspace_dir, extra_paths)
        for additional_path in additional_paths:
            try:
                stat = os.lstat(additional_path)
                import stat as stat_module
                if stat.S_ISLNK(stat.st_mode):
                    continue
                if stat.S_ISDIR(stat.st_mode):
                    if await _is_allowed_additional_directory_path(additional_path, abs_path):
                        candidate_stat = None
                        try:
                            candidate_stat = os.lstat(abs_path)
                        except Exception:
                            candidate_stat = None
                        if candidate_stat and stat_module.S_ISLNK(candidate_stat.st_mode):
                            continue
                        allowed_additional = True
                        break
                    continue
                if stat.S_ISREG(stat.st_mode) and abs_path == additional_path and abs_path.endswith(".md"):
                    allowed_additional = True
                    break
            except Exception:
                pass

    if not allowed_workspace and not allowed_additional:
        raise ValueError("path required")

    if not abs_path.endswith(".md"):
        raise ValueError("path required")

    stat_result = stat_regular_file(abs_path)
    if stat_result.missing:
        return {"text": "", "path": rel}

    try:
        result = await retry_transient_memory_read(
            lambda: read_regular_file(abs_path),
            f"read memory file {abs_path}",
        )
        content = result["buffer"].decode("utf-8")
    except Exception as err:
        if _is_file_disappeared_during_read_error(err):
            return {"text": "", "path": rel}
        raise

    return build_memory_read_result(
        content=content,
        rel_path=rel,
        from_line=from_line,
        lines=lines,
        default_lines=default_lines or DEFAULT_MEMORY_READ_LINES,
        max_chars=max_chars,
        suggest_read_fallback=allowed_workspace,
    )


async def read_agent_memory_file(
    cfg: dict,
    agent_id: str,
    rel_path: str,
    from_line: Optional[int] = None,
    lines: Optional[int] = None,
) -> dict:
    from .config_utils import (
        resolve_agent_context_limits,
        resolve_agent_workspace_dir,
        resolve_memory_search_config,
    )

    settings = resolve_memory_search_config(cfg, agent_id)
    if not settings:
        raise ValueError("memory search disabled")
    context_limits = resolve_agent_context_limits(cfg, agent_id)
    return await read_memory_file(
        workspace_dir=resolve_agent_workspace_dir(cfg, agent_id),
        extra_paths=settings.get("extraPaths"),
        rel_path=rel_path,
        from_line=from_line,
        lines=lines,
        default_lines=context_limits.get("memoryGetDefaultLines") if context_limits else None,
        max_chars=context_limits.get("memoryGetMaxChars") if context_limits else None,
    )
