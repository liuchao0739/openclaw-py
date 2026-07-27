import sys


def emit_osc_progress(percentage: float, label: str = "") -> None:
    if percentage < 0:
        percentage = 0
    if percentage > 100:
        percentage = 100

    progress = f"\x1b]1337;Progress={percentage:.0f}"
    if label:
        progress += f";{label}"
    progress += "\x07"

    sys.stdout.write(progress)
    sys.stdout.flush()


def clear_osc_progress() -> None:
    sys.stdout.write("\x1b]1337;Progress=\x07")
    sys.stdout.flush()