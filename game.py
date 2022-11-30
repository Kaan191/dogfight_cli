import curses
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import numpy as np

from base import AnimatedSprite, Plane, Projectile, TopBox, Window
from client import Client
from utils import ARENA_HEIGHT, ARENA_WIDTH, LRX, ULX, ULY
from utils import KeyPress

# === starting coordinates ===
START_COORDS_Y = np.float64(ULY + (ARENA_HEIGHT // 2))
START_COORDS_ONE = np.array((START_COORDS_Y, LRX - (ARENA_WIDTH // 4)))
START_COORDS_TWO = np.array((START_COORDS_Y, ULX + (ARENA_WIDTH // 4)))
START_ANGLE_ONE = np.pi * 1/2
START_ANGLE_TWO = np.pi * -1/2

# === keyboard key ordinals ===
ESC_KEY = 27
SPACE_KEY = 32

# === yoke dictionaries ===
P_ONE_YOKE = {
    curses.KEY_DOWN: 'up',
    curses.KEY_UP: 'down',
    SPACE_KEY: 'shoot'
}
P_TWO_YOKE = {
    ord('w'): 'up',
    ord('s'): 'down',
    ord('d'): 'shoot'
}


@dataclass
class Game(ABC):
    screen: Window
    info_box: TopBox

    planes: List[Plane] = field(default_factory=list)
    cannons: List[Projectile] = field(default_factory=list)
    animations: List[AnimatedSprite] = field(default_factory=list)

    @abstractmethod
    def _provision_planes(self) -> None:
        '''
        Define how planes are assigned .plane_id and .starting_pos
        attributes
        '''

    @abstractmethod
    def read_key(self) -> KeyPress:
        '''
        Define how a key-press is parsed based on Local or Network
        `Game` implementation
        '''

    def next_frame(self, key_presses: List[KeyPress]) -> None:
        '''
        Runner function that calculates and updates state of all
        on-screen items
        '''

        # === update planes ===
        self.planes = [p for p in self.planes if not p.for_deletion]
        for plane in self.planes:
            # read key and update plane state
            plane.parse_key(key_presses)
            if plane.fired_cannon:
                self.cannons.append(plane.fired_cannon.pop(0))

            # render updated plane state
            plane.draw(self.screen)

            # pass any generated animation to game instance
            if plane.animations:
                self.animations.extend(plane.animations)
                plane.animations = []

            # update info box
            self.info_box.update(self, key_presses)

        # === update cannon rounds ===
        self.cannons = [c for c in self.cannons if not c.for_deletion]
        for cannon in self.cannons:
            cannon.draw(self.screen, self.planes)

        # === play animations ===
        self.animations = [a for a in self.animations if not a.for_deletion]
        for anim in self.animations:
            anim.next_frame(self.screen)

    def start_game(self) -> None:
        '''
        Provisions `Planes` and waits for conditions before starting
        the game
        '''
        self.planes = self._provision_planes()

        conditions_met = False
        while not conditions_met:
            if all(p.ready for p in self.planes):
                conditions_met = True

    def reset_game(self) -> None:
        '''
        Reset state of the game
        '''
        pass

    def close_game(self) -> None:
        pass


class LocalGame(Game):

    def _provision_planes(self) -> List[Plane]:
        provisioned_planes = []

        start_coords = [START_COORDS_ONE, START_COORDS_TWO]
        start_angles = [START_ANGLE_ONE, START_ANGLE_TWO]
        for i, p in enumerate(self.planes, start=1):
            provisioned_planes.append(
                p(
                    plane_id=i,
                    color_pair=i,
                    coordinates=start_coords.pop(0),
                    angle_of_attack=start_angles.pop(0),
                    ready=True
                )
            )

        return provisioned_planes

    def read_key(self) -> List[KeyPress]:
        key_presses = []
        yokes = [P_ONE_YOKE, P_TWO_YOKE]
        key = self.screen.getch()

        for i, yoke in enumerate(yokes, start=1):
            if key in yoke:
                key_presses.append(KeyPress(i, yoke[key]))
            else:
                key_presses.append(KeyPress(i, None))

        return key_presses


@dataclass
class NetworkGame(Game):

    conn_id: str = field(init=False)
    client: Client = field(init=False)

    def __post_init__(self) -> None:
        # create client that will connect to Server
        self.conn_id = str(uuid.uuid4())
        host = os.environ['DOGFIGHT_HOST']
        port = os.environ['DOGFIGHT_PORT']
        self.client = Client(self.conn_id, host, int(port))

    def _provision_planes(self) -> List[Plane]:
        provisioned_planes = []

        # TODO: addd timeout
        # ping server and wait until two connections detected
        self.client.send({self.conn_id: None})

        while True:
            recv = self.client.receive()
            if recv and len(recv) == 2:
                uuids = list(recv.keys())
                uuids.sort()

                color_pairs = [1, 2]
                start_coords = [START_COORDS_ONE, START_COORDS_TWO]
                start_angles = [START_ANGLE_ONE, START_ANGLE_TWO]

                for u_id in uuids:
                    plane = self.planes.pop()
                    provisioned_planes.append(
                        plane(
                            plane_id=u_id,
                            color_pair=color_pairs.pop(0),
                            coordinates=start_coords.pop(0),
                            angle_of_attack=start_angles.pop(0),
                            ready=True
                        )
                    )
                return provisioned_planes

    def read_key(self) -> List[KeyPress]:
        '''
        First send "player" key, then receive keys
        '''
        key_press = self.screen.getch()
        if key_press == -1:
            key = None
        else:
            key = P_ONE_YOKE.get(key_press, -1)
        self.client.send({self.conn_id: key})

        while True:
            recv = self.client.receive()
            if recv and len(recv) == 2:
                return [KeyPress(p_id, k) for p_id, k in recv.items()]

    def close_game(self) -> None:
        _ = self.client.receive()
        self.client.close()
