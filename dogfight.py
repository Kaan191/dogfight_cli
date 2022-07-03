import curses
import os
from curses import textpad
from dataclasses import dataclass, field
from typing import Any, TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

# enables static type hinting of Window object
if TYPE_CHECKING:
    from typings.cursestyping import _CursesWindow
    Window = _CursesWindow
else:
    Window = Any

# custom Type annotation
Coordinates = NDArray[np.float64]
Vector = NDArray[np.float64]
Radian = NDArray[np.float64]

# constants
ESC = 27
PLAYER_ONE_YOKE = {
    curses.KEY_DOWN: 'up',
    curses.KEY_UP: 'down'
}
PI = np.pi
MARGIN = 5

# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'


def plus_minus(a, b) -> int:
    '''Returns +1 if a > b, or -1 if a < b'''

    return ((float(a) > float(b)) - (float(a) < float(b)))


def resolve_direction(angle: Radian) -> Vector:
    '''Converts a Radian value to a Vector with y- and x-values'''

    return np.array([
        np.round(np.cos(angle), 5),
        np.round(np.sin(angle), 5)
    ])


@dataclass
class Arena:
    stdscr: Window
    margin: int

    height: Coordinates = field(init=False)
    width: Coordinates = field(init=False)

    upper_left: Coordinates = None
    bottom_right: Coordinates = None

    def __post_init__(self):
        h, w = self.stdscr.getmaxyx()

        self.height = h - (self.margin * 2)
        self.width = w - (self.margin * 2)

        self.upper_left = np.array([self.margin, self.margin])
        self.bottom_right = np.array([h, w]) - self.margin

    def draw(self):

        textpad.rectangle(
            self.stdscr,
            uly=self.upper_left[0],
            ulx=self.upper_left[1],
            lry=self.bottom_right[0],
            lrx=self.bottom_right[1]
        )


@dataclass
class Projectile:
    '''Describes any Projectile object.

    Planes, Machine Gun and Cannon objects inherit from Projectile
    '''
    arena: Arena

    coordinates: Coordinates
    speed: Vector
    angle_of_attack: Radian
    turning_circle: Radian

    body: str

    infinite: bool = True

    def change_pitch(self, up: bool) -> None:
        ''''''
        if up:
            self.angle_of_attack += self.turning_circle
        elif not up:
            self.angle_of_attack -= self.turning_circle

    def move(self) -> None:
        '''Updates the coordinates of the Projectile object'''

        self.coordinates += (
            resolve_direction(self.angle_of_attack) *
            self.speed
        )
        self.hit_boundary()

    def hit_boundary(self) -> None:
        '''Controls consequences of hitting Arena boundary'''

        hit_y_boundary = False
        hit_x_boundary = False

        y, x = np.rint(self.coordinates)
        if y == self.arena.upper_left[0] or y == self.arena.bottom_right[0]:
            hit_y_boundary = True
        if x == self.arena.upper_left[1] or x == self.arena.bottom_right[1]:
            hit_x_boundary = True

        if not hit_y_boundary and not hit_x_boundary:
            return

        if self.infinite:
            if hit_y_boundary:
                self.coordinates[0] = (
                    y +
                    (plus_minus(self.arena.height, y) * self.arena.height) -
                    plus_minus(self.arena.height, y)
                )
            elif hit_x_boundary:
                self.coordinates[1] = (
                    x +
                    (plus_minus(self.arena.width, x) * self.arena.width) -
                    plus_minus(self.arena.width, x)
                )


@dataclass
class Plane(Projectile):
    '''Describes a Plane object

    direction is a two-item ``np.ndarray`` that contains numbers between
    -1 and 1. Going "up" would be represented by the first item (Y) at 1
    and the second itme (X) at 0. Going "down", the first item would be -1.
    Traveling "right" would have the first item (Y) at 0 and the second (X)
    at 1. Traveling "left", the second item would be -1.

    Initial state of nose coordinates are determined by direction.
    '''

    body: str = '+'
    nose: str = field(init=False)
    nose_coords: Coordinates = field(init=False)

    infinite: bool = True

    def __post_init__(self):
        self.nose_coords = (
            np.rint(self.coordinates) +
            np.rint(resolve_direction(self.angle_of_attack))
        )
        self.draw_nose()

    def move(self) -> None:

        # call base class move method
        super().move()

        # extend base class to also adjust coordinates of "nose"
        self.nose_coords = (
            np.rint(self.coordinates) +
            np.rint(resolve_direction(self.angle_of_attack))
        )
        self.draw_nose()

    def draw_nose(self) -> None:
        r'''
            \    |    /
        -+   x   +   x    +-  x   +   x
                               \  |  /

        •oOoOo•
        '''
        y, x = np.rint(resolve_direction(self.angle_of_attack))

        if y == 0:
            self.nose = '-'
        elif y == 1:
            if x == 0:
                self.nose = '|'
            elif x == -1:
                self.nose = '/'
            elif x == 1:
                self.nose = '\\'
        elif y == -1:
            if x == 0:
                self.nose = '|'
            elif x == -1:
                self.nose = '\\'
            elif x == 1:
                self.nose = '/'


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(60)  # controls refresh rate

    # create arena
    arena = Arena(stdscr, margin=MARGIN)
    arena.draw()

    # create plane
    plane_one = Plane(
        arena=arena,
        coordinates=np.array(
            [arena.bottom_right[0]/2, arena.bottom_right[1]/4]
        ),
        angle_of_attack=(PI * 1/2),
        speed=0.5,
        turning_circle=(PI * 1/8),
    )
    stdscr.addch(*np.rint(plane_one.coordinates).astype(int), plane_one.body)
    stdscr.addch(*np.rint(plane_one.nose_coords).astype(int), plane_one.nose)

    planes = [plane_one]

    while True:
        key = stdscr.getch()

        stdscr.addstr(0, 0, f'key pressed: {key}')

        if key not in PLAYER_ONE_YOKE.keys():
            key = -1

        # move plane
        for plane in planes:

            # clear previous frame
            stdscr.addch(*np.rint(plane.nose_coords).astype(int), ' ')
            stdscr.addch(*np.rint(plane.coordinates).astype(int), ' ')

            # adjust plane position
            if key in PLAYER_ONE_YOKE.keys():
                plane.change_pitch(PLAYER_ONE_YOKE[key] == 'up')
            plane.move()
            stdscr.addch(*np.rint(plane.nose_coords).astype(int), plane.nose)
            stdscr.addch(*np.rint(plane.coordinates).astype(int), plane.body)

            stdscr.addstr(1, 0, f'angle of attack: {plane.angle_of_attack}')
            stdscr.addstr(2, 0, f'coordinates: {plane.coordinates}')

    stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
