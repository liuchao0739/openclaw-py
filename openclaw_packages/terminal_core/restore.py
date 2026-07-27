import sys


def save_cursor_position() -> None:
    sys.stdout.write("\x1b[s")
    sys.stdout.flush()


def restore_cursor_position() -> None:
    sys.stdout.write("\x1b[u")
    sys.stdout.flush()


def move_cursor_up(lines: int = 1) -> None:
    sys.stdout.write(f"\x1b[{lines}A")
    sys.stdout.flush()


def move_cursor_down(lines: int = 1) -> None:
    sys.stdout.write(f"\x1b[{lines}B")
    sys.stdout.flush()


def move_cursor_left(cols: int = 1) -> None:
    sys.stdout.write(f"\x1b[{cols}D")
    sys.stdout.flush()


def move_cursor_right(cols: int = 1) -> None:
    sys.stdout.write(f"\x1b[{cols}C")
    sys.stdout.flush()


def clear_line() -> None:
    sys.stdout.write("\x1b[2K")
    sys.stdout.flush()


def clear_screen() -> None:
    sys.stdout.write("\x1b[2J\x1b[H")
    sys.stdout.flush()