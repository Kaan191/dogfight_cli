import curses
import math
import uuid
from abc import ABC, abstractmethod
from copy import copy
from dataclasses import dataclass, field
from typing import List

from base import TopBox, Window
from base import AnimatedSprite, Plane, Player, Projectile
from client import Client
from planes import BF109, P51
from utils import ARENA_HEIGHT, ARENA_WIDTH, LRX, ULX, ULY
from utils import KeyPress, Vector

# === starting coordinates ===
START_COORDS_Y = ULY + (ARENA_HEIGHT // 2)
START_COORDS_ONE = Vector(START_COORDS_Y, ULX + (ARENA_WIDTH // 4))
START_COORDS_TWO = Vector(START_COORDS_Y, LRX - (ARENA_WIDTH // 4))
START_ANGLE_ONE = math.pi * -1/2
START_ANGLE_TWO = math.pi * 1/2
CALLSIGN_ONE = Vector(ULY, ULX + 2)
CALLSIGN_TWO = Vector(ULY, LRX - 22)

# === keyboard key ordinals ===
ENTER_KEY = 10
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
    # curses items
    screen: Window
    debug_box: TopBox

    # config
    settings: dict

    # game assets
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
        start_coords = [copy(START_COORDS_ONE), copy(START_COORDS_TWO)]
        start_angles = [copy(START_ANGLE_ONE), copy(START_ANGLE_TWO)]

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

    def _draw_player_names(self) -> None:
        '''
        Draw callsigns on top arena border.

        For `NetworkGame`, because the method is called after the `Player`
        objects have been provisioned, the order of the planes has
        already been correctly configured.
        '''

        callsign_coords = [CALLSIGN_ONE, CALLSIGN_TWO]
        justify = ['left', 'right']
        for player in self.players:
            _cs = ' ' + player.callsign + ' '
            _cc = callsign_coords.pop(0)
            _j = justify.pop(0)
            if _j == 'left':
                _csf = f'{_cs:─<20}'
            elif _j == 'right':
                _csf = f'{_cs:─>20}'
            self.screen.addstr(*_cc, _csf)

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

            # update state of gun
            if plane.gun.is_reloading:
                plane.gun.reload_chamber()

            # pass any generated animation to game instance
            if plane.animations:
                self.animations.extend(plane.animations)
                plane.animations = []

            # update player info box
            player.info_box.update(player)

        # === update cannon rounds ===
        self.cannons = [c for c in self.cannons if not c.for_deletion]
        for cannon in self.cannons:
            cannon.update(self.screen, [p.plane for p in self.players])

        # === play animations ===
        self.animations = [a for a in self.animations if not a.for_deletion]
        for anim in self.animations:
            anim.next_frame(self.screen)

        # === update game info ===
        if self.debug_box:
            self.debug_box.update(self, key_presses)

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
        Reset state of plane
        '''
        start_coords = [copy(START_COORDS_ONE), copy(START_COORDS_TWO)]
        start_angles = [copy(START_ANGLE_ONE), copy(START_ANGLE_TWO)]

        for i, player in enumerate(self.players):
            if id(plane) == id(player.plane):
                plane.hull_integrity = 100
                plane.gun.rounds_in_chamber = copy(plane.gun.capacity)
                plane.coordinates = start_coords[i]
                plane.angle_of_attack = start_angles[i]
                plane.for_deletion = False
                plane.gun.reload_chamber(force=True)
            if id(plane) != id(player.plane):
                player.kills += 1

    def close_game(self) -> None:
        pass


@dataclass
class LocalGame(Game):

    def _provision_players(self) -> None:
        # get callsign information
        callsigns = [
            self.settings['player_1_callsign'],
            self.settings['player_2_callsign']
        ]
        planes = self._provision_planes()

        for i, player in enumerate(self.players, start=1):
            # bind plane to player and bring to "ready" state
            player.player_id = i
            player.callsign = callsigns.pop(0)
            player.plane = planes.pop(0)
            player.ready = True

        self._draw_player_names()

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
        host = self.settings['host_ip']
        port = self.settings['host_port']
        self.conn_id = str(uuid.uuid4())
        self.client = Client(self.conn_id, host, int(port))

    def _provision_players(self) -> None:
        # TODO: addd timeout
        # ping server and wait until two connections detected
        callsign = {'callsign': self.settings['player_1_callsign']}
        planes = self._provision_planes()

        self.client.send({self.conn_id: callsign})
        while True:
            recv = self.client.receive()
            if recv and len(recv) == 2:
                # sort uuids so clients provision players in same order
                uuids_and_callsigns = [
                    (k, v['callsign']) for k, v in recv.items()
                ]
                uuids_and_callsigns.sort(key=lambda i: i[0])
                uuids = [uc[0] for uc in uuids_and_callsigns]
                callsigns = [uc[1] for uc in uuids_and_callsigns]
                for player in self.players:
                    player.player_id = uuids.pop(0)
                    player.callsign = callsigns.pop(0)
                    player.plane = planes.pop(0)
                    player.ready = True

                self._draw_player_names()
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
