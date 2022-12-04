import argparse
import curses
import datetime as dt
import logging
import os
import pathlib
import sys

from base import Arena, TopBox, LowerLeftBox, LowerRightBox, Window
from game import LocalGame, Player, NetworkGame


# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'
os.environ['DOGFIGHT_LOCAL'] = '1'
os.environ['DOGFIGHT_LOGGING'] = '0'


def init_logger(logging_on: bool = False) -> logging.Logger:
    '''
    Return fully configured logger if `logging_on` is True, otherwise
    return standard root logger.
    '''
    dt_string = dt.datetime.now().strftime('%Y%m%d%H%M%S')

    if logging_on:
        logger = logging.getLogger('dogfight')
        logger.setLevel(logging.DEBUG)
        fh = logging.FileHandler(
            pathlib.Path(__file__).resolve().parent /
            f'client-{dt_string}.log'
        )
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        formatter.datefmt = '%Y-%m-%d %H:%M:%S'
        fh.setLevel(logging.DEBUG)
        fh.setFormatter(formatter)
        logger.addHandler(fh)
    else:
        logger = logging.getLogger()

    return logger


def main(stdscr: Window):
    # initial settings
    curses.use_default_colors()
    curses.curs_set(0)  # stops blinking cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(30)  # controls refresh rate

    # initialise logging
    if os.environ['DOGFIGHT_LOGGING'] == '1':
        logger = init_logger(True)
        logger.debug(f'=== LOGGER STARTED AT {dt.datetime.now()} ===')
    else:
        logger = init_logger(False)

    # create arena
    arena = Arena(stdscr)
    arena.draw()

    # create dynamic info box above and below arena
    debug_box = TopBox(stdscr)
    debug_box.draw()
    llbox = LowerLeftBox(stdscr)
    llbox.draw()
    lrbox = LowerRightBox(stdscr)
    lrbox.draw()

    # create Players
    players = [Player(info_box=llbox), Player(info_box=lrbox)]

    # create Game
    if os.environ['DOGFIGHT_LOCAL'] == '1':
        game = LocalGame(stdscr, debug_box, players)
    else:
        game = NetworkGame(stdscr, debug_box, players)

    while True:
        try:
            if not game.is_started:
                stdscr.refresh()
                game.start_game()
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
    parser.add_argument(
        '-L', '--logging', action='store_true', help='port of server'
    )
    args = parser.parse_args()
    if args.network:
        os.environ['DOGFIGHT_LOCAL'] = '0'
        os.environ['DOGFIGHT_HOST'] = args.host
        os.environ['DOGFIGHT_PORT'] = args.port
    if args.logging:
        os.environ['DOGFIGHT_LOGGING'] = '1'

    curses.wrapper(main)
