from __future__ import annotations

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


def is_touching_boundary(
    arena: Arena,
    coords: Coordinates
) -> tuple(bool, bool):
    '''Returns a two-tuple of bools denoting if an object is touching
    the y- or x-axis boundaries of the arena
    '''

    hit_y_boundary = False
    hit_x_boundary = False

    y, x = np.rint(coords)
    if y == arena.upper_left[0] or y == arena.bottom_right[0]:
        hit_y_boundary = True
    if x == arena.upper_left[1] or x == arena.bottom_right[1]:
        hit_x_boundary = True

    return hit_y_boundary, hit_x_boundary


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

        y, x = np.rint(self.coordinates)

        hit_y, hit_x = is_touching_boundary(self.arena, self.coordinates)
        if self.infinite:
            if hit_y:
                self.coordinates[0] = (
                    y +
                    (plus_minus(self.arena.height, y) * self.arena.height) -
                    plus_minus(self.arena.height, y)
                )
            elif hit_x:
                self.coordinates[1] = (
                    x +
                    (plus_minus(self.arena.width, x) * self.arena.width) -
                    plus_minus(self.arena.width, x)
                )

    def draw(self) -> None:
        '''Draw object on terminal screen'''

        # get reference to curses Window object and draw
        scr = self.arena.stdscr

        # clear previous render of position of object
        if not any(is_touching_boundary(self.arena, self.coordinates)):
            scr.addch(*np.rint(self.coordinates).astype(int), ' ')

        # move object to new position
        self.move()

        # render new position of object
        if not any(is_touching_boundary(self.arena, self.coordinates)):
            scr.addch(*np.rint(self.coordinates).astype(int), self.body)


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
        self.render_nose()

    def move(self) -> None:

        # call base class move method
        super().move()

        # extend base class to also adjust coordinates of "nose"
        self.nose_coords = (
            np.rint(self.coordinates) +
            np.rint(resolve_direction(self.angle_of_attack))
        )
        self.render_nose()

    def render_nose(self) -> None:
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

    def draw(self) -> None:
        '''Override base draw() method to include drawing of nose'''

        # get reference to curses Window object and draw
        scr = self.arena.stdscr

        # clear previous render of position of plane
        if not any(is_touching_boundary(self.arena, self.coordinates)):
            scr.addch(*np.rint(self.coordinates).astype(int), ' ')
        if not any(is_touching_boundary(self.arena, self.nose_coords)):
            scr.addch(*np.rint(self.nose_coords).astype(int), ' ')

        # move plane to new position
        self.move()

        # render new position of plane
        if not any(is_touching_boundary(self.arena, self.coordinates)):
            scr.addch(*np.rint(self.coordinates).astype(int), self.body)
        if not any(is_touching_boundary(self.arena, self.nose_coords)):
            scr.addch(*np.rint(self.nose_coords).astype(int), self.nose)


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(60)  # controls refresh rate

    # create arena
    arena = Arena(stdscr, margin=MARGIN)
    arena.draw()

    # keep track of objets in game
    planes = []

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
    plane_one.draw()
    planes.append(plane_one)

    while True:
        key = stdscr.getch()

        stdscr.addstr(0, 0, f'key pressed: {key}')

        if key not in PLAYER_ONE_YOKE.keys():
            key = -1

        # move plane
        for plane in planes:

            # adjust plane position
            if key in PLAYER_ONE_YOKE.keys():
                plane.change_pitch(PLAYER_ONE_YOKE[key] == 'up')
            plane.draw()

            stdscr.addstr(1, 0, f'angle of attack: {plane.angle_of_attack}')
            stdscr.addstr(2, 0, f'coordinates: {plane.coordinates}')

    stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
