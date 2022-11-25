import curses
import os
from curses import textpad
from dataclasses import dataclass, field
from typing import List

import numpy as np

from dogfight import Arena, Plane, Projectile, TopBox, Window
from planes import BF109, P51


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'

# constants
ESC_KEY = 27
SPACE_KEY = ' '
PLAYER_ONE_YOKE = {
    curses.KEY_DOWN: 'up',
    curses.KEY_UP: 'down'
}


@dataclass
class Game:
    planes: List[Plane] = field(default_factory=list)
    cannons: List[Projectile] = field(default_factory=list)


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(60)  # controls refresh rate

    # create Game
    game = Game()
    game.planes = [BF109, P51]

    # create arena
    arena = Arena(stdscr)
    arena.draw()

    # create info box above arena
    info_box = TopBox(stdscr)
    info_box.draw()

    while True:
        key = stdscr.getch()

        # move planes
        game.planes = [p for p in game.planes if not p.for_deletion]
        for i, plane in enumerate(game.planes, start=1):
            curses.init_pair(i, plane.color, curses.COLOR_BLACK)

            if key in PLAYER_ONE_YOKE.keys():
                plane.change_pitch(PLAYER_ONE_YOKE[key] == 'up')
            elif key == ord(SPACE_KEY):
                game.cannons.append(plane.fire_cannon())
            plane.draw(stdscr)

            messages = [
                f'key pressed: {key}',
                f'angle of attack: {round(plane.angle_of_attack / np.pi, 1)} * π',
                f'coordinates: {plane.coordinates}',
                f'cannon in play: {len(game.cannons)}'
            ]
            for i, m in enumerate(messages):
                info_box.write(m, line=i)

        # move projectiles
        game.cannons = [c for c in game.cannons if not c.for_deletion]
        for cannon in game.cannons:
            cannon.draw(stdscr)

        # TODO: check for hits

    stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
