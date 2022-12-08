import argparse
import curses
import datetime as dt
import logging
import os
import pathlib
import sys

from base import Arena, TopBox, LowerLeftBox, LowerRightBox, Window
from game import LocalGame, Player, NetworkGame
from menu import StartMenu

# set env variable so that xterm can show ACS_* curses characters
os.environ['NCURSES_NO_UTF8_ACS'] = '1'
os.environ['DOGFIGHT_LOCAL'] = '1'
os.environ['DOGFIGHT_LOGGING'] = '0'
os.environ['DOGFIGHT_DEBUG'] = '0'


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
    # initial curses settings
    curses.use_default_colors()
    curses.curs_set(0)  # hides cursor
    stdscr.nodelay(1)   #
    stdscr.timeout(30)  # controls refresh rate

    # initialise logging
    if os.environ['DOGFIGHT_LOGGING'] == '1':
        logger = init_logger(True)
        logger.debug(f'=== LOGGER STARTED AT {dt.datetime.now()} ===')
    else:
        logger = init_logger(False)

    # draw arena boundary
    arena = Arena(stdscr)
    arena.draw()

    # configure game with interactive menu and return settings dict
    start_menu = StartMenu(stdscr)
    settings = start_menu.open_menu()
    if settings['game_type'] == 'Local':
        game_class = LocalGame
    elif settings['game_type'] == 'Network':
        game_class = NetworkGame

    # redraw fresh arena
    arena.draw()

    # create dynamic info boxes
    if os.environ['DOGFIGHT_DEBUG'] == '1':
        debug_box = TopBox(stdscr)
        debug_box.draw()
    else:
        debug_box = None
    llbox = LowerLeftBox(stdscr)
    llbox.draw()
    lrbox = LowerRightBox(stdscr)
    lrbox.draw()

    # create Players
    players = [Player(info_box=llbox), Player(info_box=lrbox)]

    # create Game
    game = game_class(stdscr, debug_box, settings, players)
    while True:
        try:
            if not game.is_started:
                stdscr.refresh()
                game.start_game()
            key_presses = game.read_key()
            game.next_frame(key_presses)
            stdscr.refresh()
        except KeyboardInterrupt:
            game.close_game()
            sys.exit(
                f'Closed game... '
                f'({players[0].callsign}) {players[0].kills}:'
                f'{players[1].kills} ({players[1].callsign})'
            )


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-L', '--logging', action='store_true', help='enable logging'
    )
    parser.add_argument(
        '-D', '--debug', action='store_true', help='enable debug info box'
    )
    args = parser.parse_args()
    if args.logging:
        os.environ['DOGFIGHT_LOGGING'] = '1'
    if args.debug:
        os.environ['DOGFIGHT_DEBUG'] = '1'

    curses.wrapper(main)
