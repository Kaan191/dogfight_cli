import curses
import os
import sys

from base import Arena, TopBox, Window
from game import LocalGame
from planes import BF109, P51


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'


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
    game = LocalGame(screen=stdscr, info_box=info_box)
    game.planes = [BF109, P51]
    game.start_game()

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
    curses.wrapper(main)
