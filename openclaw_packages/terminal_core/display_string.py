from .ansi import visible_width, truncate_to_visible_width


class DisplayString:
    def __init__(self, text: str):
        self.text = text
        self._visible_width = visible_width(text)

    @property
    def visible_width(self) -> int:
        return self._visible_width

    def truncate(self, max_width: int) -> "DisplayString":
        return DisplayString(truncate_to_visible_width(self.text, max_width))

    def pad_right(self, width: int) -> "DisplayString":
        needed = width - self._visible_width
        if needed <= 0:
            return self
        return DisplayString(self.text + " " * needed)

    def pad_left(self, width: int) -> "DisplayString":
        needed = width - self._visible_width
        if needed <= 0:
            return self
        return DisplayString(" " * needed + self.text)

    def center(self, width: int) -> "DisplayString":
        needed = width - self._visible_width
        if needed <= 0:
            return self
        left = needed // 2
        right = needed - left
        return DisplayString(" " * left + self.text + " " * right)

    def __str__(self) -> str:
        return self.text

    def __len__(self) -> int:
        return len(self.text)