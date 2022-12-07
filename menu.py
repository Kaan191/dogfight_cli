from __future__ import annotations

import curses
import sys
from abc import ABC, abstractmethod
from configparser import ConfigParser, SectionProxy
from copy import copy
from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Tuple

import utils
from base import Window

# === keyboard key ordinals ===
ENTER_KEY = 10
Q_KEY = ord('Q')
SPACE_KEY = ord(' ')


# === Selection Actions ===


@dataclass
class Action(ABC):
    menu: Menu

    @abstractmethod
    def run_action(self) -> None:
        '''Define action'''


@dataclass
class SwitchLocal(Action):
    def run_action(self) -> None:
        for f in self.menu.fields:
            if f.label in ['Host IP', 'Host port']:
                f.is_visible = False
            else:
                f.is_visible = True
        self.menu._draw_fields()


@dataclass
class SwitchNetwork(Action):
    def run_action(self) -> None:
        for f in self.menu.fields:
            if f.label in ['Player 2 callsign', 'Player 2 plane']:
                f.is_visible = False
            else:
                f.is_visible = True
        self.menu._draw_fields()


# === Formatting strategies ===


class AlignStrategy(ABC):

    label_width: int = 0
    value_width: int = 0

    @abstractmethod
    def justify(self, label: str, value: str) -> Tuple[str, str]:
        '''
        Define how a label: value pair are justified and padded
        '''


class AlignCentre(AlignStrategy):

    label_width: int = (utils.ARENA_WIDTH - 4) // 2
    value_width: int = (utils.ARENA_WIDTH - 4) // 2

    def justify(self, label: str, value: str) -> Tuple[str, str]:
        label = f'{label:^{str(self.label_width)}}'
        value = f'{value:^{str(self.value_width)}}'
        return label, value


# === Menu fields ===


@dataclass
class Field(ABC):
    # curses screen
    screen: Window

    # configuration
    y_pos_shift: int = None
    alignment: AlignStrategy = field(default_factory=AlignCentre)
    accepts_input: bool = False

    # data
    label: str = None
    display_value: str = field(default='')
    nav_hints: List[str] = field(default_factory=list)

    # tracking state
    is_active: bool = False
    is_selection: bool = False
    is_visible: bool = True

    def __post_init__(self):
        self.label_y = utils.ULY + 5 + self.y_pos_shift
        self.label_x = utils.ULX + 2

    def _update_cursor(self) -> None:
        '''
        Helper method to place cursor at the end of a centre-justified
        text field.
        '''
        self.cursor_y = copy(self.label_y)
        self.cursor_x = (
            copy(self.label_x) +
            utils.ARENA_WIDTH // 2 +
            utils.ARENA_WIDTH // 4 +
            len(self.display_value) // 2 -
            2
        )

    @abstractmethod
    def read_key(self, key_press: int) -> None:
        '''
        Define how the .display_value variable is affected by key presses
        '''

    def display(self) -> None:
        '''
        Control how a menu field is displayed
        '''
        # collect padded & justified label: value pair
        label, value = self.alignment.justify(self.label, self.display_value)

        # format field rendering
        field_string = label + ":" + value
        if self.is_selection and self.is_active:
            field_string = label + ":" + '  <<' + value[4:-4] + '>>  '
        attr = curses.A_NORMAL
        if self.is_active:
            attr = curses.A_STANDOUT
        if not self.is_visible:
            attr = curses.A_DIM

        # update display value and cursor position
        self.screen.addstr(
            self.label_y,
            self.label_x,
            field_string,
            attr
        )
        if self.accepts_input:
            curses.curs_set(2)
        else:
            curses.curs_set(0)
        self._update_cursor()
        self.screen.move(self.cursor_y, self.cursor_x)


@dataclass
class SelectionField(Field):

    selection: List[Tuple[str, Action]] = field(default_factory=list)
    is_selection: bool = True

    def read_key(self, key_press: int) -> None:
        # get index of current display value in .selection
        curr_idx = [s[0] for s in self.selection].index(self.display_value)

        # parse key to get index of new value
        if key_press == curses.KEY_LEFT:
            curr_idx -= 1
            if curr_idx < 0:
                curr_idx = len(self.selection) - 1
        elif key_press == curses.KEY_RIGHT:
            curr_idx += 1
            if curr_idx > len(self.selection) - 1:
                curr_idx = 0

        # assign new index, grab selection tuple, execute and display
        value, action = self.selection[curr_idx]
        if action:
            action.run_action()
        self.display_value = value
        self.display()


@dataclass
class TextField(Field):

    accepts_input: bool = True

    def read_key(self, key_press: int) -> None:
        if key_press >= 33 and key_press <= 127:
            self.display_value += chr(key_press)
        if key_press == curses.KEY_BACKSPACE:
            self.display_value = self.display_value[:-1]
        self.display()


# === Menus ===


@dataclass
class Menu(ABC):
    # curses object
    screen: Window

    # menu configuration
    fields: List[Field] = field(default_factory=list)
    alignment: AlignStrategy = field(default=AlignCentre)

    # track state
    active_field_idx: int = field(default=0)

    def _go_prev_field(self):
        # unhighlight current active field
        self.fields[self.active_field_idx].is_active = False

        # set new active field, skipping 'invisible' fields
        while True:
            self.active_field_idx -= 1
            if self.active_field_idx < 0:
                self.active_field_idx = len(self.fields) - 1
            new_field = self.fields[self.active_field_idx]
            if new_field.is_visible:
                self.fields[self.active_field_idx].is_active = True
                break
            else:
                continue

        # draw updated field selection
        self._draw_fields()

    def _go_next_field(self):
        # unhighlight current active field
        self.fields[self.active_field_idx].is_active = False

        # set new active field, skipping 'invisible' fields
        while True:
            self.active_field_idx += 1
            if self.active_field_idx > len(self.fields) - 1:
                self.active_field_idx = 0
            new_field = self.fields[self.active_field_idx]
            if new_field.is_visible:
                self.fields[self.active_field_idx].is_active = True
                break
            else:
                continue

        # draw updated field selection
        self._draw_fields()

    def _draw_fields(self):
        for f in self.fields:
            f.display()

    def _update_nav_hints(self):

        standard_hints = [
            ('Q', 'Close Game'),
            ('Space', 'GO!')
        ]
        hint_string = '──'.join([
            f' < {k} > {v} ' for k, v in standard_hints
        ])

        self.screen.addstr(utils.LRY, utils.ULX + 2, hint_string)

    def open_menu(self) -> dict:

        active_field = self.fields[self.active_field_idx]
        active_field.is_active = True
        self._draw_fields()
        self._update_nav_hints()

        while True:
            try:
                key_press = self.screen.getch()

                if key_press == -1:
                    continue
                if key_press == curses.KEY_UP:
                    self._go_prev_field()
                if key_press == curses.KEY_DOWN or key_press == ENTER_KEY:
                    self._go_next_field()
                if key_press == Q_KEY:
                    sys.exit('Closed game...')
                if key_press == SPACE_KEY:
                    return self.close_menu()

                active_field = self.fields[self.active_field_idx]
                active_field.read_key(key_press)
                self.screen.refresh()
            except KeyboardInterrupt:
                sys.exit('Closed game...')

    def close_menu(self) -> dict:
        # clear screen and hide cursor
        self.screen.clear()
        curses.curs_set(0)

        # save / update settings to disk
        settings: SectionProxy
        cp = ConfigParser()
        cp.read('CONFIG.cfg')
        try:
            settings = cp['settings']
        except KeyError:
            cp.add_section('settings')
            settings = cp['settings']
        for f in self.fields:
            flabel = f.label.lower().replace(' ', '_')
            settings[flabel] = f.display_value
        with Path('CONFIG.cfg').open('w') as outfile:
            cp.write(outfile)

        # return settings dictionary
        return dict(settings)


@dataclass
class StartMenu(Menu):

    def __post_init__(self):

        # load saved settings
        cp = ConfigParser()
        cp.read('CONFIG.cfg')
        try:
            settings = cp['settings']
        except KeyError:
            settings = {}

        # create menu fields
        game = SelectionField(
            self.screen,
            y_pos_shift=0,
            label='Game type',
            display_value='Local',
            selection=[
                ('Local', SwitchLocal(self)),
                ('Network', SwitchNetwork(self))
            ]
        )

        host = TextField(
            self.screen,
            y_pos_shift=2,
            label='Host IP',
            display_value=settings.get('host_ip', ''),
            is_visible=False
        )
        port = TextField(
            self.screen,
            y_pos_shift=3,
            label='Host port',
            display_value=settings.get('host_port', ''),
            is_visible=False
        )

        player_one = TextField(
            self.screen,
            y_pos_shift=5,
            label='Player 1 callsign',
            display_value=settings.get('player_1_callsign', '')
        )
        player_one_plane = SelectionField(
            self.screen,
            y_pos_shift=6,
            label='Player 1 plane',
            display_value=settings.get('player_1_plane', 'BF109'),
            selection=[('BF109', None), ('P51', None)]
        )

        player_two = TextField(
            self.screen,
            y_pos_shift=7,
            label='Player 2 callsign',
            display_value=settings.get('player_2_callsign', '')
        )
        player_two_plane = SelectionField(
            self.screen,
            y_pos_shift=8,
            label='Player 2 plane',
            display_value=settings.get('player_2_plane', 'P51'),
            selection=[('BF109', None), ('P51', None)]
        )

        # set menu fields
        self.fields = [
            game, host, port,
            player_one, player_one_plane,
            player_two, player_two_plane
        ]
