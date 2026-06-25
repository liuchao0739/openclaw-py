"""Shared diff computation utilities for the edit tool.

Uses Python's difflib for diff generation instead of the npm diff package.
"""

from __future__ import annotations

import difflib
import re
import unicodedata
from typing import Any, TypedDict

from openclaw.agents.sessions.tools.path_utils import resolve_to_cwd


def detect_line_ending(content: str) -> str:
    """Detect whether content uses CRLF or LF line endings."""
    crlf_idx = content.find("\r\n")
    lf_idx = content.find("\n")
    if lf_idx == -1:
        return "\n"
    if crlf_idx == -1:
        return "\n"
    return "\r\n" if crlf_idx < lf_idx else "\n"


def normalize_to_lf(text: str) -> str:
    """Normalize all line endings to LF."""
    return text.replace("\r\n", "\n").replace("\r", "\n")


def restore_line_endings(text: str, ending: str) -> str:
    """Restore line endings from LF to the detected ending."""
    return text.replace("\n", "\r\n") if ending == "\r\n" else text


def _normalize_for_fuzzy_match(text: str) -> str:
    """Normalize text for fuzzy matching."""
    normalized = unicodedata.normalize("NFKC", text)
    # Strip trailing whitespace per line
    lines = normalized.split("\n")
    normalized = "\n".join(line.rstrip() for line in lines)
    # Smart single quotes → '
    normalized = re.sub(r"[\u2018\u2019\u201A\u201B]", "'", normalized)
    # Smart double quotes → "
    normalized = re.sub(r"[\u201C\u201D\u201E\u201F]", '"', normalized)
    # Various dashes/hyphens → -
    normalized = re.sub(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212]", "-", normalized)
    # Special spaces → regular space
    normalized = re.sub(r"[\u00A0\u2002-\u200A\u202F\u205F\u3000]", " ", normalized)
    return normalized


class FuzzyMatchResult(TypedDict):
    found: bool
    index: int
    matchLength: int
    usedFuzzyMatch: bool
    contentForReplacement: str


class Edit(TypedDict):
    oldText: str
    newText: str


def _fuzzy_find_text(content: str, old_text: str) -> FuzzyMatchResult:
    """Find old_text in content, trying exact match first, then fuzzy match."""
    exact_index = content.find(old_text)
    if exact_index != -1:
        return FuzzyMatchResult(
            found=True,
            index=exact_index,
            matchLength=len(old_text),
            usedFuzzyMatch=False,
            contentForReplacement=content,
        )

    fuzzy_content = _normalize_for_fuzzy_match(content)
    fuzzy_old_text = _normalize_for_fuzzy_match(old_text)
    fuzzy_index = fuzzy_content.find(fuzzy_old_text)

    if fuzzy_index == -1:
        return FuzzyMatchResult(
            found=False,
            index=-1,
            matchLength=0,
            usedFuzzyMatch=False,
            contentForReplacement=content,
        )

    return FuzzyMatchResult(
        found=True,
        index=fuzzy_index,
        matchLength=len(fuzzy_old_text),
        usedFuzzyMatch=True,
        contentForReplacement=fuzzy_content,
    )


def strip_bom(content: str) -> dict[str, str]:
    """Strip UTF-8 BOM if present."""
    if content.startswith("\uFEFF"):
        return {"bom": "\uFEFF", "text": content[1:]}
    return {"bom": "", "text": content}


def _count_occurrences(content: str, old_text: str) -> int:
    fuzzy_content = _normalize_for_fuzzy_match(content)
    fuzzy_old_text = _normalize_for_fuzzy_match(old_text)
    return fuzzy_content.count(fuzzy_old_text)


def _get_not_found_error(path: str, edit_index: int, total_edits: int) -> Exception:
    if total_edits == 1:
        return ValueError(
            f"Could not find the exact text in {path}. The old text must match exactly including all whitespace and newlines."
        )
    return ValueError(
        f"Could not find edits[{edit_index}] in {path}. The oldText must match exactly including all whitespace and newlines."
    )


def _get_duplicate_error(path: str, edit_index: int, total_edits: int, occurrences: int) -> Exception:
    if total_edits == 1:
        return ValueError(
            f"Found {occurrences} occurrences of the text in {path}. The text must be unique. Please provide more context to make it unique."
        )
    return ValueError(
        f"Found {occurrences} occurrences of edits[{edit_index}] in {path}. Each oldText must be unique. Please provide more context to make it unique."
    )


def _get_empty_old_text_error(path: str, edit_index: int, total_edits: int) -> Exception:
    if total_edits == 1:
        return ValueError(f"oldText must not be empty in {path}.")
    return ValueError(f"edits[{edit_index}].oldText must not be empty in {path}.")


def _get_no_change_error(path: str, total_edits: int) -> Exception:
    if total_edits == 1:
        return ValueError(
            f"No changes made to {path}. The replacement produced identical content."
        )
    return ValueError(f"No changes made to {path}. The replacements produced identical content.")


def apply_edits_to_normalized_content(
    normalized_content: str,
    edits: list[Edit],
    path: str,
) -> dict[str, str]:
    """Apply one or more exact-text replacements to LF-normalized content."""
    normalized_edits = [
        {"oldText": normalize_to_lf(e["oldText"]), "newText": normalize_to_lf(e["newText"])}
        for e in edits
    ]

    for i, edit in enumerate(normalized_edits):
        if len(edit["oldText"]) == 0:
            raise _get_empty_old_text_error(path, i, len(normalized_edits))

    initial_matches = [_fuzzy_find_text(normalized_content, e["oldText"]) for e in normalized_edits]
    base_content = (
        _normalize_for_fuzzy_match(normalized_content)
        if any(m["usedFuzzyMatch"] for m in initial_matches)
        else normalized_content
    )

    matched_edits: list[dict[str, Any]] = []
    for i, edit in enumerate(normalized_edits):
        match_result = _fuzzy_find_text(base_content, edit["oldText"])
        if not match_result["found"]:
            raise _get_not_found_error(path, i, len(normalized_edits))

        occurrences = _count_occurrences(base_content, edit["oldText"])
        if occurrences > 1:
            raise _get_duplicate_error(path, i, len(normalized_edits), occurrences)

        matched_edits.append({
            "editIndex": i,
            "matchIndex": match_result["index"],
            "matchLength": match_result["matchLength"],
            "newText": edit["newText"],
        })

    matched_edits.sort(key=lambda e: e["matchIndex"])
    for i in range(1, len(matched_edits)):
        prev = matched_edits[i - 1]
        curr = matched_edits[i]
        if prev["matchIndex"] + prev["matchLength"] > curr["matchIndex"]:
            raise ValueError(
                f"edits[{prev['editIndex']}] and edits[{curr['editIndex']}] overlap in {path}. "
                "Merge them into one edit or target disjoint regions."
            )

    new_content = base_content
    for edit in reversed(matched_edits):
        new_content = (
            new_content[: edit["matchIndex"]]
            + edit["newText"]
            + new_content[edit["matchIndex"] + edit["matchLength"]:]
        )

    if base_content == new_content:
        raise _get_no_change_error(path, len(normalized_edits))

    return {"baseContent": base_content, "newContent": new_content}


def generate_unified_patch(
    path: str,
    old_content: str,
    new_content: str,
    context_lines: int = 4,
) -> str:
    """Generate a standard unified patch."""
    old_lines = old_content.splitlines(keepends=True)
    new_lines = new_content.splitlines(keepends=True)
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=path,
        tofile=path,
        n=context_lines,
    )
    return "".join(diff)


class EditDiffResult(TypedDict, total=False):
    diff: str
    firstChangedLine: int | None


class EditDiffError(TypedDict):
    error: str


def generate_diff_string(
    old_content: str,
    new_content: str,
    context_lines: int = 4,
) -> EditDiffResult:
    """Generate a display-oriented diff string with line numbers and context."""
    old_lines = old_content.split("\n")
    new_lines = new_content.split("\n")
    max_line_num = max(len(old_lines), len(new_lines))
    line_num_width = len(str(max_line_num))

    matcher = difflib.SequenceMatcher(None, old_lines, new_lines)
    output: list[str] = []
    old_line_num = 1
    new_line_num = 1
    first_changed_line: int | None = None

    for tag, i1, i2, j1, j2 in matcher.get_opcodes():
        if tag == "equal":
            for line in old_lines[i1:i2]:
                ln = str(old_line_num).rjust(line_num_width)
                output.append(f" {ln} {line}")
                old_line_num += 1
                new_line_num += 1
        elif tag == "replace":
            if first_changed_line is None:
                first_changed_line = new_line_num
            for line in old_lines[i1:i2]:
                ln = str(old_line_num).rjust(line_num_width)
                output.append(f"-{ln} {line}")
                old_line_num += 1
            for line in new_lines[j1:j2]:
                ln = str(new_line_num).rjust(line_num_width)
                output.append(f"+{ln} {line}")
                new_line_num += 1
        elif tag == "delete":
            if first_changed_line is None:
                first_changed_line = new_line_num
            for line in old_lines[i1:i2]:
                ln = str(old_line_num).rjust(line_num_width)
                output.append(f"-{ln} {line}")
                old_line_num += 1
        elif tag == "insert":
            if first_changed_line is None:
                first_changed_line = new_line_num
            for line in new_lines[j1:j2]:
                ln = str(new_line_num).rjust(line_num_width)
                output.append(f"+{ln} {line}")
                new_line_num += 1

    return EditDiffResult(diff="\n".join(output), firstChangedLine=first_changed_line)


async def compute_edits_diff(
    path: str,
    edits: list[Edit],
    cwd: str,
    operations: dict[str, Any] | None = None,
) -> EditDiffResult | EditDiffError:
    """Compute the diff for one or more edit operations without applying them."""
    absolute_path = resolve_to_cwd(path, cwd)

    try:
        if operations:
            await operations["access"](absolute_path)
        else:
            import os
            if not os.path.exists(absolute_path):
                return EditDiffError(error=f"Could not edit file: {path}. Error code: ENOENT.")

        if operations:
            raw_content = await operations["readFile"](absolute_path)
        else:
            with open(absolute_path, "r", encoding="utf-8") as f:
                raw_content = f.read()

        if isinstance(raw_content, bytes):
            raw_content = raw_content.decode("utf-8")

        content = strip_bom(raw_content)["text"]
        normalized_content = normalize_to_lf(content)
        result = apply_edits_to_normalized_content(normalized_content, edits, path)
        return generate_diff_string(result["baseContent"], result["newContent"])
    except Exception as err:
        return EditDiffError(error=str(err))
