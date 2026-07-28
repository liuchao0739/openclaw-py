from __future__ import annotations

import re
from typing import Any, Dict, List, Optional

import yaml


def parse_frontmatter_block(content: str) -> Dict[str, Any]:
    block = extract_frontmatter_block(content)
    if block is None:
        return {}
    return parse_yaml_frontmatter(block)


def extract_frontmatter_block(content: str) -> Optional[str]:
    if not content.startswith("---"):
        return None

    rest = content[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    elif rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\r"):
        rest = rest[1:]

    end_idx = rest.find("\n---")
    if end_idx == -1:
        end_idx = rest.find("\r\n---")
        if end_idx == -1:
            return None

    block = rest[:end_idx]
    return block


def parse_yaml_frontmatter(block: str) -> Dict[str, Any]:
    try:
        result = yaml.safe_load(block)
        if result is None:
            return {}
        if isinstance(result, dict):
            return result
        return {}
    except yaml.YAMLError:
        return parse_line_frontmatter(block)


def parse_line_frontmatter(block: str) -> Dict[str, Any]:
    result: Dict[str, Any] = {}
    lines = block.split("\n")
    i = 0
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            i += 1
            continue

        m = re.match(r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)', stripped)
        if m:
            key = m.group(1)
            value_str = m.group(2).strip()
            if value_str:
                value = _parse_scalar(value_str)
                result[key] = value
            else:
                if i + 1 < len(lines):
                    next_line = lines[i + 1]
                    next_stripped = next_line.strip()
                    if next_stripped.startswith("- "):
                        arr: List[Any] = []
                        i += 1
                        while i < len(lines):
                            l = lines[i].strip()
                            if l.startswith("- "):
                                item = l[2:].strip()
                                arr.append(_parse_scalar(item))
                                i += 1
                            else:
                                break
                        result[key] = arr
                        continue
                    elif next_stripped.startswith(" ") or next_stripped.startswith("\t"):
                        obj: Dict[str, Any] = {}
                        i += 1
                        while i < len(lines):
                            l = lines[i]
                            ls = l.strip()
                            if not ls or ls.startswith("#"):
                                i += 1
                                continue
                            if not (l.startswith(" ") or l.startswith("\t")):
                                break
                            child_m = re.match(
                                r'^([A-Za-z_][A-Za-z0-9_-]*)\s*:\s*(.*)', ls
                            )
                            if child_m:
                                ck = child_m.group(1)
                                cv = child_m.group(2).strip()
                                if cv:
                                    obj[ck] = _parse_scalar(cv)
                                else:
                                    obj[ck] = None
                            i += 1
                        result[key] = obj
                        continue
                    else:
                        result[key] = None
                        i += 1
                        continue
                result[key] = None
                i += 1
                continue

        if ":" in stripped:
            key, _, val = stripped.partition(":")
            key = key.strip()
            val = val.strip()
            if key and key[0].isalpha() or key[0] == "_":
                result[key] = _parse_scalar(val) if val else None
        i += 1

    return result


def extract_multi_line_value(lines: List[str], start_index: int) -> tuple:
    value_lines: List[str] = []
    i = start_index
    while i < len(lines):
        line = lines[i]
        stripped = line.strip()
        if not stripped:
            value_lines.append("")
            i += 1
            break
        if line.startswith(" ") or line.startswith("\t"):
            value_lines.append(stripped)
            i += 1
        else:
            break
    return "\n".join(value_lines), i


def _parse_scalar(value: str) -> Any:
    if not value:
        return None

    if (value.startswith('"') and value.endswith('"')) or (
        value.startswith("'") and value.endswith("'")
    ):
        return value[1:-1]

    lower = value.lower()
    if lower == "true":
        return True
    if lower == "false":
        return False
    if lower == "null" or lower == "~":
        return None

    try:
        if "." in value:
            return float(value)
        return int(value)
    except ValueError:
        pass

    return value


def has_frontmatter(content: str) -> bool:
    if not content.startswith("---"):
        return False
    rest = content[3:]
    if rest.startswith("\n") or rest.startswith("\r"):
        end_idx = rest.find("\n---")
        if end_idx == -1:
            end_idx = rest.find("\r\n---")
        return end_idx != -1
    return False


def strip_frontmatter(content: str) -> str:
    if not content.startswith("---"):
        return content
    rest = content[3:]
    if rest.startswith("\n"):
        rest = rest[1:]
    elif rest.startswith("\r\n"):
        rest = rest[2:]
    elif rest.startswith("\r"):
        rest = rest[1:]

    end_idx = rest.find("\n---")
    if end_idx == -1:
        end_idx = rest.find("\r\n---")
    if end_idx == -1:
        return content

    after = rest[end_idx + 4 :] if rest[end_idx : end_idx + 4] == "\n---" else rest[end_idx + 5 :]
    if after.startswith("\n"):
        after = after[1:]
    elif after.startswith("\r\n"):
        after = after[2:]
    return after