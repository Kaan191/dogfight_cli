from __future__ import annotations

import curses
from curses import textpad
from dataclasses import dataclass, field
from typing import Any, Tuple, TYPE_CHECKING

import numpy as np
from numpy.typing import NDArray

import utils
from utils import plus_minus, resolve_direction


# enables static type hinting of Window object
if TYPE_CHECKING:
    from typings.cursestyping import _CursesWindow
    Window = _CursesWindow
else:
    Window = Any

# custom Type annotation
Scalar = np.float64
Radian = np.float64
Vector = NDArray[np.float64]
Coordinates = NDArray[np.float64]


@dataclass
class Arena:
    stdscr: Window

    def draw(self):
        textpad.rectangle(
            self.stdscr,
            uly=utils.ULY,
            ulx=utils.ULX,
            lry=utils.LRY,
            lrx=utils.LRX
        )


@dataclass
class TopBox:
    stdscr: Window

    def draw(self) -> None:
        textpad.rectangle(
            self.stdscr,
            uly=utils.ULY - 6,
            ulx=utils.ULX,
            lry=utils.ULY - 1,
            lrx=utils.LRX
        )

    def write(self, msg: str, line: int) -> None:
        textbox_top = utils.ULY - 5
        textbox_left = utils.ULX + 1
        self.stdscr.addstr(textbox_top + line, textbox_left, msg)


@dataclass
class Projectile:
    '''
    Describes any Projectile object.

    Planes, Machine Gun and Cannon objects inherit from Projectile
    '''

    coordinates: Coordinates
    angle_of_attack: Radian
    turning_circle: Radian
    speed: Scalar

    body: str
    color: int = 0
    color_pair: int = 0

    infinite: bool = False
    for_deletion: bool = False

    def change_pitch(self, up: bool) -> None:
        ''''''
        if up:
            self.angle_of_attack += self.turning_circle
        elif not up:
            self.angle_of_attack -= self.turning_circle

    def move(self) -> None:
        '''
        Updates the coordinates of the Projectile object
        '''

        # update coordinates based on speed and direction
        self.coordinates += (
            resolve_direction(self.angle_of_attack) *
            self.speed
        )

        # ...then check if boundary is hit (execute action if so)
        self.react_to_boundary()

    @staticmethod
    def hit_boundary(coordinates: Coordinates) -> Tuple[bool, bool]:
        '''
        Returns a two-tuple of bools denoting if an object is touching
        the y- or x-axis boundaries of the arena
        '''

        hit_y_boundary, hit_x_boundary = False, False
        y, x = np.rint(coordinates)

        if y <= utils.ULY or y >= utils.LRY:
            hit_y_boundary = True
        if x <= utils.ULX or x >= utils.LRX:
            hit_x_boundary = True

        return hit_y_boundary, hit_x_boundary

    def react_to_boundary(self) -> Tuple[bool, bool]:
        '''
        Controls consequences of hitting Arena boundary.

        Setting the Projectile subclass attribute "infite" to True will
        cause the object to "pop up" opposite to where the boundary was
        hit.

        If False, the Projectile instance will be deleted.
        '''

        y, x = np.rint(self.coordinates)

        hit_y, hit_x = self.hit_boundary(self.coordinates)
        if self.infinite:
            if hit_y:
                self.coordinates[0] = (
                    y +
                    (plus_minus(utils.ARENA_HEIGHT, y) * utils.ARENA_HEIGHT) -
                    plus_minus(utils.ARENA_HEIGHT, y)
                )
            elif hit_x:
                self.coordinates[1] = (
                    x +
                    (plus_minus(utils.ARENA_WIDTH, x) * utils.ARENA_WIDTH) -
                    plus_minus(utils.ARENA_WIDTH, x)
                )
        else:
            if hit_y or hit_x:
                self.for_deletion = True

    def draw(self, screen: Window) -> None:
        '''Draw object on terminal screen'''

        # clear previous render of position of object
        if not any(self.hit_boundary(self.coordinates)):
            screen.addch(*np.rint(self.coordinates).astype(int), ' ')

        # move object to new position
        self.move()

        # render new position of object
        if not any(self.hit_boundary(self.coordinates)):
            screen.addch(*np.rint(self.coordinates).astype(int), self.body)

    def mark_for_deletion(self) -> None:
        self.for_deletion = True


@dataclass
class Cannon(Projectile):
    turning_circle: Radian = field(default=0)
    speed: Scalar = field(default=3.0)

    body: str = '•'


@dataclass
class Plane(Projectile):
    '''
    Describes a Plane object

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

    def draw(self, screen: Window) -> None:
        '''Override base draw() method to include drawing of nose'''

        # clear previous render of position of plane
        if not any(self.hit_boundary(self.coordinates)):
            screen.addch(*np.rint(self.coordinates).astype(int), ' ')
        if not any(self.hit_boundary(self.nose_coords)):
            screen.addch(*np.rint(self.nose_coords).astype(int), ' ')

        # move plane to new position
        self.move()

        # render new position of plane
        if not any(self.hit_boundary(self.coordinates)):
            screen.addch(
                *np.rint(self.coordinates).astype(int),
                self.body,
                curses.color_pair(self.color_pair)
            )
        if not any(self.hit_boundary(self.nose_coords)):
            screen.addch(
                *np.rint(self.nose_coords).astype(int),
                self.nose,
                curses.color_pair(self.color_pair)
            )

    def fire_cannon(self) -> Cannon:

        return Cannon(
            coordinates=np.copy(self.coordinates),
            turning_circle=0,
            angle_of_attack=np.copy(self.angle_of_attack)
        )
