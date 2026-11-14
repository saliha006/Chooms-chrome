"""Where the next brick is (F9). Until real localization lands, the operator says how many bricks are in the zone."""


class CountLocator:
    """Reports `n` bricks in the pick zone, then an empty zone."""

    def __init__(self, n: int):
        self._left = n

    def next_brick(self) -> bool:
        if self._left == 0:
            return False
        self._left -= 1
        return True
