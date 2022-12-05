from __future__ import annotations

import copy
import curses
import math
import os
from collections import namedtuple
from dataclasses import dataclass
from typing import Any, Tuple, TYPE_CHECKING, Union

# enables static type hinting of Window object
if TYPE_CHECKING:
    from typings.cursestyping import _CursesWindow
    Window = _CursesWindow
else:
    Window = Any


# === helper data structures ===
KeyPress = namedtuple('KeyPress', 'player_id key')


# === arena dimensions ===
# in order to centre the Arena, we need to calculate where
# the upper left and bottom right boundaries are.
# the upper left x-value is half the width of the terminal
# divided by half the width of Arena; the bottom right x-value
# is that amount subtracted from the width of terminal.
ARENA_HEIGHT = 20
ARENA_WIDTH = 80
TERM_HEIGHT = os.get_terminal_size().lines
TERM_WIDTH = os.get_terminal_size().columns

# x- and y-axis shifts for centring drawn objects
Y_SHIFT = (TERM_HEIGHT // 2) - (ARENA_HEIGHT // 2)
X_SHIFT = (TERM_WIDTH // 2) - (ARENA_WIDTH // 2)

# shifted anchor coordinates
ULY = 0 + Y_SHIFT
ULX = 0 + X_SHIFT
LRY = ARENA_HEIGHT + Y_SHIFT
LRX = ARENA_WIDTH + X_SHIFT


@dataclass
class Vector:
    y: float
    x: float

    def resolve(self) -> Tuple[int, int]:
        return round(self.y), round(self.x)

    def __copy__(self):
        return Vector(copy.copy(self.y), copy.copy(self.x))

    def __round__(self) -> Vector:
        return Vector(round(self.y), round(self.x))

    def __iter__(self):
        return iter((self.y, self.x))

    def __getitem__(self, key: slice) -> float:
        return [self.y, self.x][key]

    def __add__(self, other: Union[int, Vector]) -> Vector:
        if isinstance(other, Vector):
            return Vector(self.y + other.y, self.x + other.x)
        elif isinstance(other, float) or isinstance(other, int):
            return Vector(self.y + other, self.x + other)
        else:
            raise TypeError('can only operate on another Vector')

    def __sub__(self, other: Union[int, Vector]) -> Vector:
        if isinstance(other, Vector):
            return Vector(self.y - other.y, self.x - other.x)
        elif isinstance(other, float) or isinstance(other, int):
            return Vector(self.y - other, self.x - other)
        else:
            raise TypeError('can only operate on another Vector')

    def __mul__(self, other: Union[int, Vector]) -> Vector:
        if isinstance(other, Vector):
            return Vector(self.y * other.y, self.x * other.x)
        elif isinstance(other, float) or isinstance(other, int):
            return Vector(self.y * other, self.x * other)
        else:
            raise TypeError('can only operate on another Vector')


def resolve_direction(angle: float) -> Vector:
    '''
    Converts a Radian value to a Vector with y- and x-values
    '''

    y = round(math.cos(angle), 5)
    x = round(math.sin(angle), 5)
    return Vector(y, x)


def get_char(screen: Window, y: int, x: int) -> str:
    char_ordinal = screen.inch(y, x)
    char = chr(char_ordinal & curses.A_CHARTEXT)
    return char
