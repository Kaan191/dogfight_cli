import argparse
import curses
import os
import sys

from base import Arena, TopBox, LowerLeftBox, LowerRightBox, Window
from game import LocalGame, NetworkGame
from planes import BF109, P51


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'
os.environ['DOGFIGHT_LOCAL'] = '1'


# def _init_game(players: 'Player', boxes: 'InfoBox') -> Game:
#     pass


def main(stdscr: Window):
    # initial settings
    curses.use_default_colors()
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(30)  # controls refresh rate

    # create arena
    arena = Arena(stdscr)
    arena.draw()

    # create dynamic info box above and below arena
    boxes = []
    for box in [TopBox, LowerLeftBox, LowerRightBox]:
        _box = box(stdscr)
        _box.draw()
        boxes.append(_box)

    # create Game
    if os.environ['DOGFIGHT_LOCAL'] == '1':
        game = LocalGame(stdscr, *boxes)
    else:
        game = NetworkGame(stdscr, *boxes)
    game.planes = [BF109, P51]
    try:
        game.start_game()
    except Exception as e:
        sys.exit(e.with_traceback())

    while True:
        try:
            key_presses = game.read_key()
            game.next_frame(key_presses)
            stdscr.refresh()
        except KeyboardInterrupt:
            print('Exiting game...')
            game.close_game()
            sys.exit(1)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-n', '--network', action='store_true', help='flag for network game'
    )
    parser.add_argument(
        '-H', '--host', help='IP address of server'
    )
    parser.add_argument(
        '-P', '--port', default='51515', help='port of server'
    )
    args = parser.parse_args()
    if args.network:
        os.environ['DOGFIGHT_LOCAL'] = '0'
        os.environ['DOGFIGHT_HOST'] = args.host
        os.environ['DOGFIGHT_PORT'] = args.port

    curses.wrapper(main)
