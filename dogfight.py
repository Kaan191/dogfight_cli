import curses
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from typings.cursestyping import _CursesWindow
    Window = _CursesWindow
else:
    from typing import Any
    Window = Any


def main(stdscr: Window):
    # clear screen
    stdscr.clear()

    for i in range(0, 11):
        v = i-10
        stdscr.addstr(i, 0, '10 divided by {} is {}'.format(v, 10/v))

    stdscr.refresh()
    stdscr.getkey()


curses.wrapper(main)
