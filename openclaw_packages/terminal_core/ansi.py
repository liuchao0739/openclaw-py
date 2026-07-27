import re
import sys
import unicodedata

ANSI_CSI_PATTERN = r"\x1b\[[\x20-\x3f]*[\x40-\x7e]"
ANSI_OSC_PATTERN = r"\x1b\][^\x07\x1b]*(?:\x1b\\|\x07)"

ANSI_CSI_REGEX = re.compile(ANSI_CSI_PATTERN)
ANSI_OSC_REGEX = re.compile(ANSI_OSC_PATTERN)
ANSI_SEQUENCE_REGEX = re.compile(f"{ANSI_OSC_PATTERN}|{ANSI_CSI_PATTERN}")


def strip_ansi(input: str) -> str:
    return ANSI_OSC_REGEX.sub("", ANSI_CSI_REGEX.sub("", input))


def split_graphemes(input: str) -> list[str]:
    if not input:
        return []
    try:
        import unicodedata
        result = []
        i = 0
        while i < len(input):
            if sys.version_info >= (3, 12):
                from unicodedata import segment
                seg = segment(input, i)
                result.append(input[i:i+seg])
                i += seg
            else:
                result.append(input[i])
                i += 1
        return result
    except:
        return list(input)


def sanitize_for_log(v: str) -> str:
    c0_start = chr(0x00)
    c0_end = chr(0x1f)
    del_char = chr(0x7f)
    c1_start = chr(0x80)
    c1_end = chr(0x9f)
    control_chars_regex = re.compile(f"[{c0_start}-{c0_end}{del_char}{c1_start}-{c1_end}]")
    return strip_ansi(v).replace(control_chars_regex, "")


def is_zero_width_code_point(code_point: int) -> bool:
    return (
        (code_point >= 0x0300 and code_point <= 0x036f) or
        (code_point >= 0x1ab0 and code_point <= 0x1aff) or
        (code_point >= 0x1dc0 and code_point <= 0x1dff) or
        (code_point >= 0x20d0 and code_point <= 0x20ff) or
        (code_point >= 0xfe20 and code_point <= 0xfe2f) or
        (code_point >= 0xfe00 and code_point <= 0xfe0f) or
        code_point == 0x200d
    )


def is_full_width_code_point(code_point: int) -> bool:
    if code_point < 0x1100:
        return False
    return (
        code_point <= 0x115f or
        code_point == 0x2329 or
        code_point == 0x232a or
        (code_point >= 0x2e80 and code_point <= 0x3247 and code_point != 0x303f) or
        (code_point >= 0x3250 and code_point <= 0x4dbf) or
        (code_point >= 0x4e00 and code_point <= 0xa4c6) or
        (code_point >= 0xa960 and code_point <= 0xa97c) or
        (code_point >= 0xac00 and code_point <= 0xd7a3) or
        (code_point >= 0xf900 and code_point <= 0xfaff) or
        (code_point >= 0xfe10 and code_point <= 0xfe19) or
        (code_point >= 0xfe30 and code_point <= 0xfe6b) or
        (code_point >= 0xff01 and code_point <= 0xff60) or
        (code_point >= 0xffe0 and code_point <= 0xffe6) or
        (code_point >= 0x1aff0 and code_point <= 0x1aff3) or
        (code_point >= 0x1aff5 and code_point <= 0x1affb) or
        (code_point >= 0x1affd and code_point <= 0x1affe) or
        (code_point >= 0x1b000 and code_point <= 0x1b2ff) or
        (code_point >= 0x1f200 and code_point <= 0x1f251) or
        (code_point >= 0x20000 and code_point <= 0x3fffd)
    )


EMOJI_LIKE_PATTERN = re.compile(r"[\p{Extended_Pictographic}\p{Regional_Indicator}\u20e3]", re.UNICODE)


def grapheme_width(grapheme: str) -> int:
    if not grapheme:
        return 0
    if EMOJI_LIKE_PATTERN.search(grapheme):
        return 2

    saw_printable = False
    for char in grapheme:
        code_point = ord(char)
        if is_zero_width_code_point(code_point):
            continue
        if is_full_width_code_point(code_point):
            return 2
        saw_printable = True
    return 1 if saw_printable else 0


def visible_width(input: str) -> int:
    return sum(grapheme_width(grapheme) for grapheme in split_graphemes(strip_ansi(input)))


def truncate_to_visible_width(input: str, max_width: int) -> str:
    if max_width <= 0:
        return ""
    if visible_width(input) <= max_width:
        return input

    ANSI_SEQUENCE_REGEX.lastindex = 0
    out = ""
    used = 0
    pos = 0
    budget_spent = False

    def append_visible(segment: str) -> None:
        nonlocal out, used, budget_spent
        if budget_spent:
            return
        for grapheme in split_graphemes(segment):
            width = grapheme_width(grapheme)
            if used + width > max_width:
                budget_spent = True
                return
            out += grapheme
            used += width

    match = ANSI_SEQUENCE_REGEX.search(input)
    while match:
        append_visible(input[pos:match.start()])
        out += match.group(0)
        pos = match.end()
        match = ANSI_SEQUENCE_REGEX.search(input, pos)

    append_visible(input[pos:])
    return out