import argparse
import curses
import os
import sys

from base import Arena, TopBox, Window
from game import LocalGame, NetworkGame
from planes import BF109, P51


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'
os.environ['DOGFIGHT_LOCAL'] = '1'


def main(stdscr: Window):
    # initial settings
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(50)  # controls refresh rate

    # create arena
    arena = Arena(stdscr)
    arena.draw()

    # create info box above arena
    info_box = TopBox(stdscr)
    info_box.draw()

    # create Game
    if os.environ['DOGFIGHT_LOCAL'] == '1':
        game = LocalGame(screen=stdscr, info_box=info_box)
    else:
        game = NetworkGame(screen=stdscr, info_box=info_box)
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
