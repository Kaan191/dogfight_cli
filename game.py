import curses
import os
import uuid
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List

import numpy as np

from base import InfoBox, TopBox, Window
from base import AnimatedSprite, Plane, Projectile
from client import Client
from planes import BF109, P51
from utils import ARENA_HEIGHT, ARENA_WIDTH, LRX, ULX, ULY
from utils import KeyPress

# === starting coordinates ===
START_COORDS_Y = np.float64(ULY + (ARENA_HEIGHT // 2))
START_COORDS_ONE = np.array((START_COORDS_Y, ULX + (ARENA_WIDTH // 4)))
START_COORDS_TWO = np.array((START_COORDS_Y, LRX - (ARENA_WIDTH // 4)))
START_ANGLE_ONE = np.pi * -1/2
START_ANGLE_TWO = np.pi * 1/2

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
class Player:
    player_id: str = None

    conn: Client = None
    plane: Plane = None
    info_box: InfoBox = None

    kills: int = 0
    ready: bool = False

    def parse_key(self, key_presses: List[KeyPress]) -> None:
        '''
        '''
        for k in key_presses:
            if k.player_id == self.player_id:
                key = k.key
                # isolate navigation controls
                if key in ['up', 'down']:
                    self.plane._change_pitch(up=key == 'up')
                # ...otherwise fire cannon
                if key == 'shoot':
                    cannon_round = self.plane._fire_cannon()
                    if cannon_round:
                        self.plane.fired_cannon.append(cannon_round)


@dataclass
class Game(ABC):
    # curses items
    screen: Window
    info_box: TopBox

    # track game assets
    players: List[Player]
    cannons: List[Projectile] = field(default_factory=list)
    animations: List[AnimatedSprite] = field(default_factory=list)

    # track game state
    is_started: bool = False

    def _provision_planes(self) -> List[Plane]:
        '''
        '''
        provisioned_planes = []

        planes = [BF109, P51]
        color_pairs = [1, 2]
        start_coords = [np.copy(START_COORDS_ONE), np.copy(START_COORDS_TWO)]
        start_angles = [np.copy(START_ANGLE_ONE), np.copy(START_ANGLE_TWO)]

        for p in planes:
            provisioned_planes.append(
                p(
                    color_pair=color_pairs.pop(0),
                    coordinates=start_coords.pop(0),
                    angle_of_attack=start_angles.pop(0),
                )
            )

        return provisioned_planes

    @abstractmethod
    def _provision_players(self) -> None:
        '''
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
        for player in self.players:
            plane = player.plane

            # check if was killed in previous frame
            if plane.for_deletion:
                self.reset_plane(plane)

            # render updated plane state
            player.parse_key(key_presses)
            if plane.fired_cannon:
                self.cannons.append(plane.fired_cannon.pop(0))
            plane.draw(self.screen)

            # pass any generated animation to game instance
            if plane.animations:
                self.animations.extend(plane.animations)
                plane.animations = []

            # update player info box
            player.info_box.update(plane)

        # === update cannon rounds ===
        self.cannons = [c for c in self.cannons if not c.for_deletion]
        for cannon in self.cannons:
            cannon.update(self.screen, [p.plane for p in self.players])

        # === play animations ===
        self.animations = [a for a in self.animations if not a.for_deletion]
        for anim in self.animations:
            anim.next_frame(self.screen)

        # === update game info ===
        self.info_box.update(self, key_presses)

    def start_game(self) -> None:
        '''
        Provisions `Planes` and waits for conditions before starting
        the game
        '''
        self._provision_players()

        conditions_met = False
        while not conditions_met:
            if all(p.ready for p in self.players):
                conditions_met = True

        self.is_started = True

    def reset_plane(self, plane: Plane) -> None:
        '''
        Reset state of the game
        '''
        start_coords = [np.copy(START_COORDS_ONE), np.copy(START_COORDS_TWO)]
        start_angles = [np.copy(START_ANGLE_ONE), np.copy(START_ANGLE_TWO)]

        for i, player in enumerate(self.players):
            if id(plane) == id(player.plane):
                plane.hull_integrity = 100
                plane.gun.rounds_in_chamber = np.copy(plane.gun.capacity)
                plane.coordinates = start_coords[i]
                plane.angle_of_attack = start_angles[i]
                plane.for_deletion = False
            if id(plane) != id(player.plane):
                player.kills += 1

    def close_game(self) -> None:
        pass


@dataclass
class LocalGame(Game):

    def _provision_players(self) -> None:
        planes = self._provision_planes()
        for i, player in enumerate(self.players, start=1):
            player.player_id = i
            player.plane = planes.pop(0)
            player.ready = True

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
        host = os.environ['DOGFIGHT_HOST']
        port = os.environ['DOGFIGHT_PORT']
        self.conn_id = str(uuid.uuid4())
        self.client = Client(self.conn_id, host, int(port))

    def _provision_players(self) -> None:
        # TODO: addd timeout
        # ping server and wait until two connections detected
        planes = self._provision_planes()

        self.client.send({self.conn_id: None})
        while True:
            recv = self.client.receive()
            if recv and len(recv) == 2:
                uuids = list(recv.keys())
                uuids.sort()
                for player in self.players:
                    player.player_id = uuids.pop(0)
                    player.plane = planes.pop(0)
                    player.ready = True
                break

    def read_key(self) -> List[KeyPress]:
        '''
        First send "player" key, then receive keys from server
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
