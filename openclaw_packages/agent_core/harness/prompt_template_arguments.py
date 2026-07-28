from __future__ import annotations

import re

from .harness_types import PromptTemplate


def parse_command_args(args_string: str) -> list[str]:
    args: list[str] = []
    current = ""
    in_quote: str | None = None
    has_token = False

    for char in args_string:
        if in_quote:
            if char == in_quote:
                in_quote = None
            else:
                has_token = True
                current += char
        elif char in ('"', "'"):
            has_token = True
            in_quote = char
        elif char.isspace():
            if has_token:
                args.append(current)
                current = ""
                has_token = False
        else:
            has_token = True
            current += char

    if has_token:
        args.append(current)
    return args


def _parse_safe_non_negative_integer(raw: str) -> int | None:
    try:
        parsed = int(raw)
    except (TypeError, ValueError):
        return None
    if parsed < 0:
        return None
    return parsed


def substitute_args(content: str, args: list[str]) -> str:
    result = content

    def _replace_num(match: re.Match) -> str:
        num = match.group(1)
        parsed = _parse_safe_non_negative_integer(num)
        if parsed is None or parsed <= 0:
            return ""
        if parsed - 1 < len(args):
            return args[parsed - 1]
        return ""

    result = re.sub(r"\$(\d+)", _replace_num, result)

    def _replace_range(match: re.Match) -> str:
        start_str = match.group(1)
        length_str = match.group(2)
        parsed_start = _parse_safe_non_negative_integer(start_str)
        if parsed_start is None:
            return ""
        start = parsed_start - 1
        if start < 0:
            start = 0
        if length_str is not None:
            length = _parse_safe_non_negative_integer(length_str)
            if length is None:
                return ""
            return " ".join(args[start : start + length])
        return " ".join(args[start:])

    result = re.sub(r"\$\{@:(\d+)(?::(\d+))?\}", _replace_range, result)

    all_args = " ".join(args)
    result = result.replace("$ARGUMENTS", all_args)
    result = result.replace("$@", all_args)
    return result


def format_prompt_template_invocation(
    template: PromptTemplate,
    args: list[str] | None = None,
) -> str:
    args = args or []
    return substitute_args(template.content, args)
