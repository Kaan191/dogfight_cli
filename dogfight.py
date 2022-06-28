# -*- coding: utf-8 -*-
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

# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'


@dataclass
class Arena:
    stdscr: Window
    margin: int

    upper_left: Coordinates = None
    bottom_right: Coordinates = None

    def __post_init__(self):
        h, w = self.stdscr.getmaxyx()

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
    coordinates: Coordinates
    speed: Vector
    angle_of_attack: Radian
    turning_circle: Radian

    body: str


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
    nose: str = '-'
    nose_coords: Coordinates = field(init=False)

    def __post_init__(self):
        self.nose_coords = (
            np.rint(self.coordinates) +
            np.rint(resolve_direction(self.angle_of_attack))
        )


def resolve_direction(angle: float) -> Vector:

    return np.array([
        np.round(np.cos(angle), 5),
        np.round(np.sin(angle), 5)
    ])


def change_pitch(plane: Plane, up: bool) -> None:
    ''''''
    if up:
        plane.angle_of_attack += plane.turning_circle
    elif not up:
        plane.angle_of_attack -= plane.turning_circle


def move_plane(plane: Plane) -> None:
    '''Updates the coordinates of the plane'''
    plane.coordinates += (
        resolve_direction(plane.angle_of_attack) *
        plane.speed
    )
    plane.nose_coords = (
        np.rint(plane.coordinates) +
        np.rint(resolve_direction(plane.angle_of_attack))
    )


def draw_plane_nose(plane: Plane) -> None:
    '''
        \    |    /                     # noqa
    -+   x   +   x    +-  x   +   x
                           \  |  /      # noqa

    •oOoOo•
    '''
    prev = plane.nose
    y, x = np.rint(resolve_direction(plane.angle_of_attack))
    if y == 0:
        if x == 0:
            plane.nose = prev
        else:
            plane.nose = '-'
    elif y == 1:
        if x == 0:
            plane.nose = '|'
        elif x == -1:
            plane.nose = '/'
        elif x == 1:
            plane.nose = '\\'
    elif y == -1:
        if x == 0:
            plane.nose = '|'
        elif x == -1:
            plane.nose = '\\'
        elif x == 1:
            plane.nose = '/'


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)
    stdscr.nodelay(1)
    stdscr.timeout(60)

    arena = Arena(stdscr, margin=5)
    arena.draw()

    plane_one = Plane(
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

            stdscr.addch(*np.rint(plane.nose_coords).astype(int), ' ')
            stdscr.addch(*np.rint(plane.coordinates).astype(int), ' ')

            if key in PLAYER_ONE_YOKE.keys():
                change_pitch(plane, PLAYER_ONE_YOKE[key] == 'up')
            move_plane(plane)

            draw_plane_nose(plane)
            stdscr.addch(*np.rint(plane.nose_coords).astype(int), plane.nose)
            stdscr.addch(*np.rint(plane.coordinates).astype(int), plane.body)

            stdscr.addstr(1, 0, f'angle of attack: {plane.angle_of_attack}')
            stdscr.addstr(2, 0, f'coordinates: {plane.coordinates}')
            stdscr.addstr(3, 0, f'direction resolved: {resolve_direction(plane.angle_of_attack)}')

    stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
