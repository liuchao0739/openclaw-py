from __future__ import annotations

from typing import Optional

from .fs_utils import stat_regular_file
from .multimodal import (
    DISABLED_MULTIMODAL_SETTINGS,
    MemoryMultimodalSettings,
    classify_memory_multimodal_path,
)
from .string_utils import normalize_string_entries, unique_strings


CHARS_PER_TOKEN_ESTIMATE = 4


def ensure_dir(dir_path: str) -> str:
    import os
    os.makedirs(dir_path, exist_ok=True)
    return dir_path


def normalize_rel_path(value: str) -> str:
    import re
    trimmed = value.strip()
    trimmed = re.sub(r"^[./]+", "", trimmed)
    return trimmed.replace("\\", "/")


def expand_home_path(value: str) -> str:
    import os
    if value == "~":
        return os.path.expanduser("~")
    if value.startswith("~/") or value.startswith("~\\"):
        return os.path.join(os.path.expanduser("~"), value[2:])
    return value


def normalize_extra_memory_paths(workspace_dir: str, extra_paths: Optional[list] = None) -> list:
    import os
    if not extra_paths:
        return []
    resolved = []
    for value in normalize_string_entries(extra_paths):
        expanded = expand_home_path(value)
        resolved.append(os.path.abspath(expanded) if os.path.isabs(expanded) else os.path.abspath(os.path.join(workspace_dir, expanded)))
    return unique_strings(resolved)


def is_memory_path(rel_path: str) -> bool:
    from .config_utils import CANONICAL_ROOT_MEMORY_FILENAME
    normalized = normalize_rel_path(rel_path)
    if not normalized:
        return False
    if normalized == CANONICAL_ROOT_MEMORY_FILENAME or normalized.lower() == "dreams.md":
        return True
    return normalized.startswith("memory/")


def is_allowed_memory_file_path(file_path: str, multimodal: Optional[MemoryMultimodalSettings] = None) -> bool:
    if file_path.endswith(".md"):
        return True
    settings = multimodal or DISABLED_MULTIMODAL_SETTINGS
    return classify_memory_multimodal_path(file_path, settings) is not None


def estimate_string_chars(text: str) -> int:
    return len(text)


def cosine_similarity(a: list, b: list) -> float:
    if not a or not b:
        return 0.0
    length = min(len(a), len(b))
    dot = 0.0
    norm_a = 0.0
    norm_b = 0.0
    for i in range(length):
        av = a[i] if i < len(a) else 0
        bv = b[i] if i < len(b) else 0
        dot += av * bv
        norm_a += av * av
        norm_b += bv * bv
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / ((norm_a ** 0.5) * (norm_b ** 0.5))


def parse_embedding(raw: str) -> list:
    import json
    try:
        parsed = json.loads(raw)
        return parsed if isinstance(parsed, list) else []
    except (json.JSONDecodeError, ValueError):
        return []


def remap_chunk_lines(chunks: list, line_map: Optional[list]) -> None:
    if not line_map:
        return
    for chunk in chunks:
        chunk["start_line"] = line_map[chunk["start_line"] - 1] if chunk["start_line"] - 1 < len(line_map) else chunk["start_line"]
        chunk["end_line"] = line_map[chunk["end_line"] - 1] if chunk["end_line"] - 1 < len(line_map) else chunk["end_line"]


def chunk_markdown(content: str, chunking: dict) -> list:
    from .embedding_inputs import build_text_embedding_input
    from .hash import hash_text

    lines = content.split("\n")
    if not lines:
        return []

    max_chars = max(32, chunking.get("tokens", 0) * CHARS_PER_TOKEN_ESTIMATE)
    overlap_chars = max(0, chunking.get("overlap", 0) * CHARS_PER_TOKEN_ESTIMATE)
    chunks = []

    current = []
    current_chars = 0

    def flush() -> None:
        if not current:
            return
        first_entry = current[0]
        last_entry = current[-1]
        if not first_entry or not last_entry:
            return
        text = "\n".join(entry["line"] for entry in current)
        chunks.append({
            "start_line": first_entry["lineNo"],
            "end_line": last_entry["lineNo"],
            "text": text,
            "hash": hash_text(text),
            "embedding_input": build_text_embedding_input(text),
        })

    def carry_overlap() -> None:
        nonlocal current, current_chars
        if overlap_chars <= 0 or not current:
            current = []
            current_chars = 0
            return
        acc = 0
        kept = []
        for i in range(len(current) - 1, -1, -1):
            entry = current[i]
            acc += estimate_string_chars(entry["line"]) + 1
            kept.insert(0, entry)
            if acc >= overlap_chars:
                break
        current = kept
        current_chars = acc

    for i, line in enumerate(lines):
        line_no = i + 1
        segments = []
        if not line:
            segments.append("")
        else:
            for start in range(0, len(line), max_chars):
                coarse = line[start:start + max_chars]
                if estimate_string_chars(coarse) > max_chars:
                    fine_step = max(1, chunking.get("tokens", 1))
                    j = 0
                    while j < len(coarse):
                        end = min(j + fine_step, len(coarse))
                        if end < len(coarse):
                            code = ord(coarse[end - 1])
                            if 0xd800 <= code <= 0xdbff:
                                end += 1
                        segments.append(coarse[j:end])
                        j = end
                else:
                    segments.append(coarse)

        for segment in segments:
            line_size = estimate_string_chars(segment) + 1
            if current_chars + line_size > max_chars and current:
                flush()
                carry_overlap()
            current.append({"line": segment, "lineNo": line_no})
            current_chars += line_size

    flush()
    return chunks


async def run_with_concurrency(tasks: list, limit: int) -> list:
    import asyncio
    sem = asyncio.Semaphore(limit)
    results = []
    has_error = False
    first_error = None

    async def run_task(task):
        nonlocal first_error, has_error
        async with sem:
            try:
                return await task()
            except Exception as e:
                if not has_error:
                    first_error = e
                    has_error = True
                raise

    coros = [run_task(t) for t in tasks]
    for coro in coros:
        try:
            results.append(await coro)
        except Exception:
            pass

    if has_error:
        raise first_error
    return results
