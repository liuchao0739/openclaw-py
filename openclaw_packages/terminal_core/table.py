from typing import List, Optional, Tuple

from .ansi import visible_width, truncate_to_visible_width


def render_table(rows: List[List[str]], col_widths: Optional[List[int]] = None, padding: int = 1) -> str:
    if not rows:
        return ""

    if col_widths is None:
        col_widths = []
        for col_idx in range(len(rows[0])):
            max_width = max(visible_width(row[col_idx]) for row in rows)
            col_widths.append(max_width)

    lines = []

    for row_idx, row in enumerate(rows):
        cells = []
        for col_idx, cell in enumerate(row):
            width = col_widths[col_idx] if col_idx < len(col_widths) else visible_width(cell)
            truncated = truncate_to_visible_width(cell, width)
            padded = truncated + " " * (width - visible_width(truncated) + padding)
            cells.append(padded)
        lines.append("".join(cells))

    return "\n".join(lines)