import os

import numpy as np
from numpy.typing import NDArray

Radian = np.float64
Vector = NDArray[np.float64]

# === arena dimensions ===
# in order to centre the Arena, we need to calculate where
# the upper left and bottom right boundaries are.
# the upper left x-value is half the width of the terminal
# divided by half the width of Arena; the bottom right x-value
# is that amount subtracted from the width of terminal.
ARENA_HEIGHT = 40
ARENA_WIDTH = 80
TERM_HEIGHT = os.get_terminal_size().lines
TERM_WIDTH = os.get_terminal_size().columns
ULX = (TERM_WIDTH // 2) - (ARENA_WIDTH // 2)
ULY = (TERM_HEIGHT // 2) - (ARENA_HEIGHT // 2)
LRX = TERM_WIDTH - ULX
LRY = TERM_HEIGHT - ULY


def plus_minus(a, b) -> int:
    '''Returns +1 if a > b, or -1 if a < b'''

    return ((float(a) > float(b)) - (float(a) < float(b)))


def resolve_direction(angle: Radian) -> Vector:
    '''
    Converts a Radian value to a Vector with y- and x-values
    '''

    return np.array([
        np.round(np.cos(angle), 5),
        np.round(np.sin(angle), 5)
    ])
