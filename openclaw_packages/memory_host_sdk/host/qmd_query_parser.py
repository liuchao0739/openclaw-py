from __future__ import annotations

import json
import re
from typing import Any, Dict, List, Optional

from .error_utils import format_error_message
from .string_utils import normalize_lowercase_string_or_empty


def _warn_qmd_query_parse_error(message: str) -> None:
    import sys
    sys.stderr.write(f"qmd query returned invalid JSON: {message}\n")


def _is_qmd_no_results_output(raw: str) -> bool:
    lines = [line for line in raw.split("\n") if line.strip()]
    for line in lines:
        normalized = normalize_lowercase_string_or_empty(re.sub(r"\s+", " ", line))
        if _is_qmd_no_results_line(normalized):
            return True
    return False


def _is_qmd_no_results_line(line: str) -> bool:
    if line in ("no results found", "no results found."):
        return True
    return bool(re.match(
        r"^(?:\[[^\]]+\]\s*)?(?:(?:warn(?:ing)?|info|error|qmd)\s*:\s*)+no results found\.?$",
        line,
    ))


def _summarize_qmd_stderr(raw: str) -> str:
    return raw if len(raw) <= 120 else raw[:117] + "..."


def _parse_qmd_query_result_array(raw: str) -> Optional[List[Dict[str, Any]]]:
    try:
        parsed = json.loads(raw)
        if not isinstance(parsed, list):
            return None
        results = []
        for item in parsed:
            if not isinstance(item, dict):
                continue
            record = item
            result = {
                "docid": record.get("docid") if isinstance(record.get("docid"), str) else None,
                "score": record.get("score") if isinstance(record.get("score"), (int, float)) else None,
                "collection": record.get("collection") if isinstance(record.get("collection"), str) else None,
                "file": record.get("file") if isinstance(record.get("file"), str) else None,
                "snippet": record.get("snippet") if isinstance(record.get("snippet"), str) else None,
                "body": record.get("body") if isinstance(record.get("body"), str) else None,
                "startLine": _parse_qmd_line_number(record.get("start_line", record.get("startLine"))),
                "endLine": _parse_qmd_line_number(record.get("end_line", record.get("endLine"))),
            }
            results.append(result)
        return results
    except Exception:
        return None


def _parse_qmd_line_number(value: Any) -> Optional[int]:
    if isinstance(value, int) and value > 0:
        return value
    if isinstance(value, float) and value > 0 and value == int(value):
        return int(value)
    return None


def _extract_first_json_array(raw: str) -> Optional[str]:
    start = raw.find("[")
    if start < 0:
        return None
    depth = 0
    in_string = False
    escaped = False
    i = start
    while i < len(raw):
        char = raw[i]
        if in_string:
            if escaped:
                escaped = False
                i += 1
                continue
            if char == "\\":
                escaped = True
            elif char == '"':
                in_string = False
            i += 1
            continue
        if char == '"':
            in_string = True
            i += 1
            continue
        if char == "[":
            depth += 1
        elif char == "]":
            depth -= 1
            if depth == 0:
                return raw[start:i + 1]
        i += 1
    return None


def parse_qmd_query_json(stdout: str, stderr: str) -> List[Dict[str, Any]]:
    trimmed_stdout = stdout.strip()
    trimmed_stderr = stderr.strip()

    stdout_is_marker = len(trimmed_stdout) > 0 and _is_qmd_no_results_output(trimmed_stdout)
    stderr_is_marker = len(trimmed_stderr) > 0 and _is_qmd_no_results_output(trimmed_stderr)

    if stdout_is_marker or (not trimmed_stdout and stderr_is_marker):
        return []

    if not trimmed_stdout:
        context = f" (stderr: {_summarize_qmd_stderr(trimmed_stderr)})" if trimmed_stderr else ""
        message = f"stdout empty{context}"
        _warn_qmd_query_parse_error(message)
        raise RuntimeError(f"qmd query returned invalid JSON: {message}")

    try:
        parsed = _parse_qmd_query_result_array(trimmed_stdout)
        if parsed is not None:
            return parsed
        noisy_payload = _extract_first_json_array(trimmed_stdout)
        if not noisy_payload:
            raise RuntimeError("qmd query JSON response was not an array")
        fallback = _parse_qmd_query_result_array(noisy_payload)
        if fallback is not None:
            return fallback
        raise RuntimeError("qmd query JSON response was not an array")
    except Exception as err:
        message = format_error_message(err)
        _warn_qmd_query_parse_error(message)
        raise RuntimeError(f"qmd query returned invalid JSON: {message}") from err
