from __future__ import annotations

import curses
import time
from abc import ABC, abstractmethod
from curses import textpad
from dataclasses import dataclass, field
from typing import List, Optional, Tuple

import numpy as np

import utils
from utils import plus_minus, resolve_direction, Window
from utils import Coordinates, Radian, Scalar


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
class InfoBox(ABC):

    # curses window for "drawing" on
    stdscr: Window

    # where info box is placed relative to `Arena`
    anchor: str = field(default='top')

    # dimensions to be defined in subclass __post_init__ method
    uly: int = field(init=False)
    ulx: int = field(init=False)
    lry: int = field(init=False)
    lrx: int = field(init=False)

    def draw(self) -> None:
        '''
        Draw box
        '''
        textpad.rectangle(
            self.stdscr,
            uly=self.uly,
            ulx=self.ulx,
            lry=self.lry,
            lrx=self.lrx
        )

    def _write(self, msg: str, line: int) -> None:
        '''
        Helper function to control placement of messages
        '''
        textbox_top = self.uly + 1
        textbox_left = self.ulx + 1
        self.stdscr.addstr(textbox_top + line, textbox_left, msg)

    @abstractmethod
    def update(self, game, *kwargs) -> None:
        '''
        Define logic for interactive game display
        '''


@dataclass
class TopBox(InfoBox):

    def __post_init__(self):
        self.uly = utils.ULY - 6
        self.ulx = utils.ULX
        self.lry = utils.ULY - 1
        self.lrx = utils.LRX

    def update(self, game, key_presses) -> None:
        keys_pressed = ', '.join([str(k.key) for k in key_presses])
        integrity = ', '.join(
            [str(p.plane.hull_integrity) for p in game.players]
        )
        # angle = f'{round(plane.angle_of_attack / np.pi, 1)} * π'

        messages = {
            'keys pressed': keys_pressed,
            'cannon in play': str(len(game.cannons)),
            'animations': str(len(game.animations)),
            'integrity': integrity
        }

        for i, m in enumerate(messages.items()):
            key = f'{m[0]: <15}: '
            val = f'{m[1]: <15}'
            self._write(key + val, line=i)


@dataclass
class LowerLeftBox(InfoBox):
    anchor: str = 'bottom'

    def __post_init__(self):
        self.uly = utils.LRY + 1
        self.ulx = utils.ULX
        self.lry = utils.LRY + 4
        self.lrx = utils.LRX - 1 - utils.ARENA_WIDTH // 2

        self.plane_idx: int = 0

    def update(self, plane: Plane) -> None:
        messages = {
            'ammo': plane.gun.rounds_in_chamber / plane.gun.capacity,
            'integrity': plane.hull_integrity / 100
        }

        width = (utils.ARENA_WIDTH // 2) - 1
        for i, m in enumerate(messages.items()):
            bar_width = int(float(m[1]) * int(width * 0.6))
            key = f'{m[0]: <{int(width * 0.4) - 1}}: '
            val = f'{"|" * (bar_width - 1): <{int(width * 0.6) - 1}}'
            self._write(key + val, line=i)


@dataclass
class LowerRightBox(InfoBox):
    anchor: str = 'bottom'

    def __post_init__(self):
        self.uly = utils.LRY + 1
        self.ulx = utils.ULX + 1 + utils.ARENA_WIDTH // 2
        self.lry = utils.LRY + 4
        self.lrx = utils.LRX

        self.plane_idx: int = 1

    def update(self, plane: Plane) -> None:
        messages = {
            'ammo': plane.gun.rounds_in_chamber / plane.gun.capacity,
            'integrity': plane.hull_integrity / 100
        }

        width = (utils.ARENA_WIDTH // 2) - 1
        for i, m in enumerate(messages.items()):
            bar_width = int(float(m[1]) * int(width * 0.6))
            key = f'{m[0]: <{int(width * 0.4) - 1}}: '
            val = f'{"|" * (bar_width - 1): <{int(width * 0.6) - 1}}'
            self._write(key + val, line=i)


@dataclass
class AnimatedSprite:
    '''
    Define sprite art objects with a `.next_frame` method for animating
    '''
    coordinates: Coordinates
    angle_of_attack: Radian = 0
    speed: Scalar = 0

    frames: list = field(init=False)
    colors: list = field(init=False)

    for_deletion: bool = False

    @property
    def resolved_coords(self) -> Tuple[int, int]:
        '''
        Converts the "real" coordinates stored as `np.float64` into
        rounded integers to place the object on a curses `Window`
        '''
        y, x = np.rint(self.coordinates).astype(int)
        return (y, x)

    @property
    def inside_arena(self) -> bool:
        '''
        Returns True if coordinates are inside the arena boundary
        '''
        y, x = self.resolved_coords
        inside_y = y > utils.ULY and y < utils.LRY
        inside_x = x > utils.ULX and x < utils.LRX

        if inside_y and inside_x:
            return True
        else:
            return False

    def next_frame(self, screen: Window) -> None:
        '''
        Switches sprite to next 'frame' in `.frames` list

        First checks that the resolved coordinates of the newly-created
        `AnimatedSprite` are in an empty cell. Once empty, the animation
        is started.

        Animation plays until 'frames' are exhausted.
        '''

        # clear previous frame if moving
        if self.inside_arena:
            screen.addch(*self.resolved_coords, ' ')

        # update coordinates
        self.coordinates += (
            resolve_direction(self.angle_of_attack) *
            self.speed
        )

        # draw next frame
        if self.frames:
            if self.inside_arena:
                screen.addch(*self.resolved_coords, self.frames.pop(0))
            else:
                self.frames.pop(0)
        else:
            self.for_deletion = True


@dataclass
class PlaneSmoke(AnimatedSprite):

    def __post_init__(self):
        self.frames: list = list('••ooO0oo00oo••')
        self.colors: list = list('11111111111111')


@dataclass
class PlaneExplosion(AnimatedSprite):

    def __post_init__(self):
        self.frames: List[str] = list('x+x+x+•••.........')
        self.colors: List[str] = list('111111111111111111')


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

    infinite: bool = False
    animations: List[AnimatedSprite] = field(default_factory=list)

    for_deletion: bool = False

    @property
    def resolved_coords(self) -> Tuple[int, int]:
        '''
        Converts the "real" coordinates stored as `np.float64` into
        rounded integers to place the object on a curses `Window`
        '''
        y, x = np.rint(self.coordinates).astype(int)
        return (y, x)

    def _change_pitch(self, up: bool) -> None:
        ''''''
        if up:
            self.angle_of_attack += self.turning_circle
        elif not up:
            self.angle_of_attack -= self.turning_circle

    def _hit_boundary(self, y: int, x: int) -> Tuple[bool, bool]:
        '''
        Returns a two-tuple of bools denoting if an object is touching
        the y- or x-axis boundaries of the arena
        '''

        hit_y_boundary, hit_x_boundary = False, False

        if y <= utils.ULY or y >= utils.LRY:
            hit_y_boundary = True
        if x <= utils.ULX or x >= utils.LRX:
            hit_x_boundary = True

        return hit_y_boundary, hit_x_boundary

    def _react_to_boundary(self) -> Tuple[bool, bool]:
        '''
        Controls consequences of hitting Arena boundary.

        Setting the Projectile subclass attribute "infite" to True will
        cause the object to "pop up" opposite to where the boundary was
        hit.

        If False, the Projectile instance will be deleted.
        '''

        y, x = self.resolved_coords
        hit_y, hit_x = self._hit_boundary(y, x)
        if self.infinite:
            if hit_y:
                self.coordinates[0] = (
                    y +
                    (
                        plus_minus(utils.TERM_HEIGHT//2, y) *
                        utils.ARENA_HEIGHT
                    ) -
                    plus_minus(utils.TERM_HEIGHT//2, y)
                )
            elif hit_x:
                self.coordinates[1] = (
                    x +
                    (
                        plus_minus(utils.TERM_WIDTH//2, x) *
                        utils.ARENA_WIDTH
                    ) -
                    plus_minus(utils.TERM_WIDTH//2, x)
                )
        else:
            if hit_y or hit_x:
                self.for_deletion = True

    def _move(self) -> None:
        '''
        Updates the coordinates of the Projectile object
        '''

        # update coordinates based on speed and direction
        self.coordinates += (
            resolve_direction(self.angle_of_attack) *
            self.speed
        )

        # ...then check if boundary is hit (execute action if so)
        self._react_to_boundary()

    def draw(self, screen: Window) -> None:
        '''Draw object on terminal screen'''

        # clear previous render of position of object
        if not any(self._hit_boundary(*self.resolved_coords)):
            screen.addch(*self.resolved_coords, ' ')

        # move object to new position
        self._move()

        # render new position of object
        if not any(self._hit_boundary(*self.resolved_coords)):
            screen.addch(*self.resolved_coords, self.body)

    def hit_check(self, obj: Projectile) -> bool:
        '''
        Pass `Coordinates` of another object and return True if equal
        to the resolved coordinates of the `Projectile` instance.
        '''
        obj_y, obj_x = np.rint(obj.coordinates).astype(int)
        if self.resolved_coords == (obj_y, obj_x):
            return True
        else:
            return False


@dataclass
class Cannon(Projectile):
    turning_circle: Radian = field(default=0)
    speed: Scalar = field(default=1.0)

    body: str = '•'

    damage: int = 0

    def _check_hits(self, planes: List[Plane]) -> bool:
        hit = False
        for plane in planes:
            if plane.hit_check(self):
                plane.hull_integrity -= self.damage
                hit = True
                self.for_deletion = True
                # play a "hit" animation
                for i in range(-1, 2):
                    plane.animations.append(
                        PlaneExplosion(
                            coordinates=self.resolved_coords,
                            angle_of_attack=self.angle_of_attack + (i / 5),
                            speed=self.speed * 0.5
                        )
                    )

        return hit

    def update(self, screen: Window, planes: List[Plane]) -> None:
        '''Draw object on terminal screen and calculate hit/damage'''

        # clear previous render of position of object
        if not any(self._hit_boundary(*self.resolved_coords)):
            screen.addch(*self.resolved_coords, ' ')

        # check if cannon hits plane. If no hit, move the cannon
        if not self._check_hits(planes):
            self._move()
            # render new position of cannon if the next move wasn't a hit
            if not self._check_hits(planes):
                if not any(self._hit_boundary(*self.resolved_coords)):
                    screen.addch(*self.resolved_coords, self.body)


@dataclass
class Gun:

    # gun configuration
    capacity: int
    reload_time: int
    damage: int

    # gun state
    rounds_in_chamber: int = field(init=False)
    last_fired: Optional[int] = None
    reloading: bool = False

    def __post_init__(self):

        self.rounds_in_chamber = np.copy(self.capacity)

    def fire(
        self,
        coordinates: Tuple[int, int],
        angle_of_attack: Radian
    ) -> Optional[Cannon]:

        # store fired cannon in variable
        c = None

        # check if gun is reloading; reset gun if reloading complete
        if self.reloading:
            if time.monotonic() - self.last_fired > self.reload_time:
                self.rounds_in_chamber = np.copy(self.capacity)
                self.reloading = False
                self.rounds_in_chamber -= 1
                c = Cannon(coordinates, angle_of_attack, damage=self.damage)
        else:
            self.rounds_in_chamber -= 1
            c = Cannon(coordinates, angle_of_attack, damage=self.damage)

        # if cannon was fired, check if chamber is empty and mark
        # as reloading if so
        if c:
            if self.rounds_in_chamber == 0:
                self.last_fired = time.monotonic()
                self.reloading = True
            return c


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

    color_pair: int = None
    gun: Gun = None

    body: str = '+'
    nose: str = field(init=False)
    nose_coords: Tuple[int, int] = field(init=False)

    infinite: bool = True

    hull_integrity: int = 100
    fired_cannon: List[Cannon] = field(default_factory=list)

    def __post_init__(self):

        # initialise curses color pair
        curses.init_pair(self.color_pair, self.color, -1)

        # resolve nose coordinates and draw
        self.nose_coords = tuple(
            self.resolved_coords +
            np.rint(resolve_direction(self.angle_of_attack))
        )
        self._render_nose()

    def _render_nose(self) -> None:
        r'''
            \    |    /
        -+   x   +   x    +-  x   +   x
                               \  |  /

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

    def _fire_cannon(self) -> Optional[Cannon]:
        '''
        Attempt to fire a cannon. If Gun.is_reloading is True, None is
        returned.
        '''

        # cannon starting position just ahead of the plane's nose
        start_coords = np.copy(
            self.nose_coords +
            np.rint(resolve_direction(self.angle_of_attack))
        )

        c = self.gun.fire(start_coords, np.copy(self.angle_of_attack))
        if c:
            return c

    def _move(self) -> None:

        # call base class move method
        super()._move()

        # extend base class to also adjust coordinates of "nose"
        self.nose_coords = tuple(
            self.resolved_coords +
            np.rint(resolve_direction(self.angle_of_attack))
        )
        self._render_nose()

    def draw(self, screen: Window) -> None:
        '''Override base draw() method to include drawing of nose'''

        # clear previous render of position of plane
        if not any(self._hit_boundary(*self.resolved_coords)):
            screen.addch(*self.resolved_coords, ' ')
        if not any(self._hit_boundary(*self.nose_coords)):
            screen.addch(*np.rint(self.nose_coords).astype(int), ' ')

        # create `PlaneSmoke` instance prior to move if hull integrity
        # below threshold
        if self.hull_integrity < 40:
            anims_at_coords = [
                a for a in self.animations
                if a.resolved_coords == self.resolved_coords
            ]
            if not anims_at_coords:
                self.animations.append(PlaneSmoke(self.resolved_coords))

        # move plane to new position
        self._move()

        # render new position of plane if not destroyed
        # otherwise, mark plane for deletion and don't draw
        if self.hull_integrity > 0:
            if not any(self._hit_boundary(*self.resolved_coords)):
                screen.addch(
                    *self.resolved_coords,
                    self.body,
                    curses.color_pair(self.color_pair)
                )
            if not any(self._hit_boundary(*self.nose_coords)):
                screen.addch(
                    *np.rint(self.nose_coords).astype(int),
                    self.nose,
                    curses.color_pair(self.color_pair)
                )
        else:
            for i in range(-2, 3):
                self.animations.append(
                    PlaneExplosion(
                        coordinates=self.resolved_coords,
                        angle_of_attack=self.angle_of_attack + (i / 3),
                        speed=self.speed * 0.7
                    )
                )
            self.for_deletion = True
