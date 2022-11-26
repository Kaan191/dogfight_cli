import curses
import os
from dataclasses import dataclass, field
from typing import List

from dogfight import Arena, AnimatedSprite, Plane, Projectile, TopBox, Window
from planes import BF109, P51


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'

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
class Game:
    planes: List[Plane] = field(default_factory=list)
    cannons: List[Projectile] = field(default_factory=list)
    animations: List[AnimatedSprite] = field(default_factory=list)


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(60)  # controls refresh rate

    # create Game
    game = Game()
    game.planes = [
        BF109(plane_id=1, yoke_dict=P_ONE_YOKE, hull_integrity=15),
        P51(plane_id=2, yoke_dict=P_TWO_YOKE, hull_integrity=10)
    ]

    # create arena
    arena = Arena(stdscr)
    arena.draw()

    # create info box above arena
    info_box = TopBox(stdscr)
    info_box.draw()

    while True:
        key = stdscr.getch()

        # === update planes ===
        game.planes = [p for p in game.planes if not p.for_deletion]
        for plane in game.planes:
            # read key and update plane state
            plane.parse_key(key)
            if plane.fired_cannon:
                game.cannons.append(plane.fired_cannon.pop(0))

            # render updated plane state
            plane.draw(stdscr)

            # pass any generated animation to game instance
            if plane.animations:
                game.animations.extend(plane.animations)
                plane.animations = []

            # update info box
            messages = [
                f'key pressed: {key}',
                # f'angle of attack: {round(plane.angle_of_attack / np.pi, 1)} * π',
                f'coordinates: {plane.resolved_coords}',
                f'cannon in play: {len(game.cannons)}',
                f'animations: {len(plane.animations)}',
            ]
            for i, m in enumerate(messages):
                info_box.write(m, line=i)

        # === update cannon rounds ===
        game.cannons = [c for c in game.cannons if not c.for_deletion]
        for cannon in game.cannons:
            cannon.draw(stdscr)

        # === play animations ===
        game.animations = [a for a in game.animations if not a.for_deletion]
        for anim in game.animations:
            anim.next_frame(stdscr)

        # TODO: check for hits

    stdscr.refresh()


if __name__ == '__main__':
    curses.wrapper(main)
