"""
Minimal OPL3-style tracker UI.

Keys:
  Arrow keys / hjkl : Move cursor
  Space             : Toggle drum step (X/.)
  s                 : Start / stop transport
  + or =            : Increase BPM
  -                 : Decrease BPM
  Tab               : Switch Pattern / Instrument / Channel view
  0-9               : Enter digits in numeric fields
  x / X             : Toggle boolean fields
  Enter             : Commit numeric entry
  Backspace         : Delete digit
  q                 : Quit
"""

import curses
import time
from dataclasses import dataclass


PATTERN_ROWS = ["BD", "SD", "TT", "CY", "HH"]
INSTRUMENTS = ["BD1", "BD2", "SD", "TT", "CY", "HH"]
CHANNELS = ["CH1", "CH2", "CH3"]
STEPS = 64

# Color pair IDs
COLOR_ACTIVE = 1
COLOR_BEAT = 2
COLOR_CURSOR = 3
COLOR_HEADER = 4
COLOR_STATUS = 5


@dataclass
class Instrument:
    name: str
    attack: int = 15
    decay: int = 7
    sustain_level: int = 8
    release: int = 4
    volume: int = 50
    waveform: int = 0
    freq_mult: int = 0
    sustain: bool = False


@dataclass
class Channel:
    name: str
    midi_note: int = 50
    fm: bool = True
    feedback: int = 0


@dataclass
class TrackerState:
    patterns: dict[str, list[bool]]
    instruments: dict[str, Instrument]
    channels: dict[str, Channel]
    bpm: int = 140


def make_state():
    state = TrackerState(
        patterns={name: [False] * STEPS for name in PATTERN_ROWS},
        instruments={name: Instrument(name) for name in INSTRUMENTS},
        channels={name: Channel(name) for name in CHANNELS},
    )
    for i in range(STEPS):
        state.patterns["BD"][i] = i % 16 in (0, 6)
        state.patterns["SD"][i] = i % 16 in (4, 10)
        state.patterns["TT"][i] = i % 32 % 12 in (2, )
        state.patterns["CY"][i] = i % 32 in (10,) or i == 31
        state.patterns["HH"][i] = i % 32 in (0, 2, 30)

    return state


class TrackerUI:
    def __init__(self, stdscr):
        from examples.tracker.audio import OPL3Engine
        self.stdscr = stdscr
        self.state = make_state()
        self.engine = OPL3Engine(tracker_state=self.state)

        self.view = "pattern"  # pattern, instrument, channel
        self.pattern_row = 0
        self.pattern_col = 0

        self.instrument_index = 0
        self.instrument_field_index = 0
        self.instrument_edit_buffer = ""

        self.channel_index = 0
        self.channel_field_index = 0
        self.channel_edit_buffer = ""

        self.play_position = 0
        self.set_bpm(self.state.bpm)

        self.instrument_fields = [
            ("attack", "num", 0, 15),
            ("decay", "num", 0, 15),
            ("sustain", "bool", None, None),
            ("sustain_level", "num", 0, 15),
            ("release", "num", 0, 15),
            ("volume", "num", 0, 63),
            ("waveform", "num", 0, 7),
            ("freq_mult", "num", 0, 15),
        ]

        self.channel_fields = [
            ("midi_note", "num", 1, 127),
            ("fm", "bool", None, None),
            ("feedback", "num", 0, 7),
        ]

    def set_bpm(self, bpm: int):
        self.state.bpm = bpm
        # Four steps per musical beat: 16th notes.
        self.step_duration = 60.0 / self.state.bpm / 4.0
        self.engine.mark_dirty()

    def current_pattern(self):
        name = PATTERN_ROWS[self.pattern_row]
        return self.state.patterns[name]

    def current_instrument(self):
        name = INSTRUMENTS[self.instrument_index]
        return self.state.instruments[name]

    def current_channel(self):
        name = CHANNELS[self.channel_index]
        return self.state.channels[name]

    def toggle_transport(self):
        if self.engine.playing:
            self.engine.stop()
        else:
            self.engine.start()

    def advance_transport(self):
        self.engine.schedule_ahead()
        
        if self.engine.playing:
            elapsed_steps = int(
                (
                    self.engine.chip.current_sample
                    - self.engine.pattern_start_sample
                )
                // self.engine.samples_per_step()
            )

            self.play_position = elapsed_steps % STEPS

    def draw(self):
        self.stdscr.erase()
        height, width = self.stdscr.getmaxyx()

        transport = "PLAYING" if self.engine.playing else "STOPPED"

        self.stdscr.addstr(
            0, 0,
            "OPL3 TRACKER  [s: start/stop]  "
            "[+/-: BPM]  [Tab: view]  [q: quit]",
            curses.color_pair(COLOR_HEADER) | curses.A_BOLD,
        )

        self.stdscr.addstr(
            1, 0,
            f"View: {self.view.upper():10}   "
            f"Transport: {transport}   "
            f"BPM: {self.state.bpm}",
        )

        if self.view == "pattern":
            self.draw_pattern()
        elif self.view == "instrument":
            self.draw_instruments()
        else:
            self.draw_channels()

        self.draw_status(height - 1, width)
        self.stdscr.refresh()

    def draw_pattern(self):
        tens = ""
        units = ""

        for step in range(STEPS):
            number = f"{step + 1:02d}"
            tens += number[0]
            units += number[1]

        for row, text in enumerate((tens, units)):
            y = 3 + row

            for step in range(STEPS):
                attr = curses.color_pair(COLOR_HEADER)

                # Emphasize every fourth step.
                if step % 4 == 0:
                    attr |= curses.A_BOLD

                self.stdscr.addch(y, 5 + step, text[step], attr)

        for row, name in enumerate(PATTERN_ROWS):
            y = 6 + row
            self.stdscr.addstr(y, 0, f"{name:>4} ")

            for col in range(STEPS):
                active = self.state.patterns[name][col]
                value = "X" if active else "."
                attr = curses.A_NORMAL

                if active:
                    attr |= curses.color_pair(COLOR_ACTIVE) | curses.A_BOLD
                elif col % 4 == 0:
                    attr |= curses.color_pair(COLOR_BEAT)

                if row == self.pattern_row and col == self.pattern_col:
                    attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD

                if self.engine.playing and col == self.play_position:
                    attr |= curses.A_UNDERLINE

                self.stdscr.addch(y, 5 + col, value, attr)

    def draw_instruments(self):
        inst = self.current_instrument()

        self.stdscr.addstr(
            3, 0,
            f"Instrument: {inst.name}",
            curses.color_pair(COLOR_HEADER) | curses.A_BOLD,
        )

        self.stdscr.addstr(
            4, 2,
            "Left/Right: instrument   Up/Down: parameter",
        )

        for i, (field, kind, minimum, maximum) in enumerate(
                self.instrument_fields
        ):
            y = 6 + i
            value = getattr(inst, field)

            if kind == "bool":
                rendered = "X" if value else "."
            else:
                rendered = str(value)

            label = f"{field:<15}"
            attr = curses.A_NORMAL

            if i == self.instrument_field_index:
                attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD

                if self.instrument_edit_buffer:
                    rendered = self.instrument_edit_buffer + "_"

            self.stdscr.addstr(y, 2, label)
            self.stdscr.addstr(y, 20, rendered, attr)

        self.stdscr.addstr(
            len(self.instrument_fields) + 8, 2,
            "Numeric: 0-9, Enter, Backspace | Boolean: x/X or Space",
        )

    def draw_channels(self):
        channel = self.current_channel()

        self.stdscr.addstr(
            3, 0,
            f"Channel: {channel.name}",
            curses.color_pair(COLOR_HEADER) | curses.A_BOLD,
            )

        self.stdscr.addstr(
            4, 2,
            "Left/Right: channel   Up/Down: parameter",
        )

        fields = self.fields_for_current_channel()

        for i, (field, kind, minimum, maximum) in enumerate(fields):
            y = 6 + i
            value = getattr(channel, field)

            if kind == "bool":
                rendered = "X" if value else "."
            else:
                rendered = str(value)

            label = f"{field:<15}"
            attr = curses.A_NORMAL

            if i == self.channel_field_index:
                attr = curses.color_pair(COLOR_CURSOR) | curses.A_BOLD

                if self.channel_edit_buffer:
                    rendered = self.channel_edit_buffer + "_"

            self.stdscr.addstr(y, 2, label)
            self.stdscr.addstr(y, 20, rendered, attr)

        self.stdscr.addstr(
            len(fields) + 8, 2,
            "Numeric: 0-9, Enter, Backspace | Boolean: x/X or Space",
            )

    def fields_for_current_channel(self):
        if self.channel_index == 0:
            return self.channel_fields

        # Channels 2 and 3 do not expose BD's FM/feedback controls.
        return [self.channel_fields[0]]

    def draw_status(self, y, width):
        if self.view == "pattern":
            status = (
                f"Pattern {PATTERN_ROWS[self.pattern_row]} | "
                f"Step {self.pattern_col + 1:02d}/{STEPS} | "
                f"BPM {self.state.bpm} | "
                f"Space: toggle | "
                f"s: {'stop ' if self.engine.playing else 'start'} | "
                f"Tab: instruments"
            )

        elif self.view == "instrument":
            inst = self.current_instrument()
            field, kind, minimum, maximum = (
                self.instrument_fields[self.instrument_field_index]
            )
            value = getattr(inst, field)

            if kind == "bool":
                range_text = "bool"
            else:
                range_text = f"{minimum}-{maximum}"

            status = (
                f"{inst.name:3} | "
                + "{:17} | ".format(f"{field} = {value}")
                + f"{range_text} | "
                f"Tab: channels"
            )

        else:
            channel = self.current_channel()
            fields = self.fields_for_current_channel()
            field, kind, minimum, maximum = fields[self.channel_field_index]
            value = getattr(channel, field)

            if kind == "bool":
                range_text = "bool"
            else:
                range_text = f"{minimum}-{maximum}"

            status = (
                f"{channel.name} | "
                + "{:17} | ".format(f"{field} = {value}")
                + f"{range_text} | "
                f"Tab: patterns"
            )

        self.stdscr.addnstr(
            y, 0, status, width - 1,
            curses.color_pair(COLOR_STATUS) | curses.A_BOLD,
        )

    def edit_pattern(self, key):
        if key in (curses.KEY_UP, ord("k")):
            self.pattern_row = (self.pattern_row - 1) % len(PATTERN_ROWS)
        elif key in (curses.KEY_DOWN, ord("j")):
            self.pattern_row = (self.pattern_row + 1) % len(PATTERN_ROWS)
        elif key in (curses.KEY_LEFT, ord("h")):
            self.pattern_col = (self.pattern_col - 1) % STEPS
        elif key in (curses.KEY_RIGHT, ord("l")):
            self.pattern_col = (self.pattern_col + 1) % STEPS
        elif key == ord(" "):
            pattern = self.current_pattern()
            pattern[self.pattern_col] = not pattern[self.pattern_col]
            self.engine.mark_dirty()

    def move_instrument_cursor(self, key):
        if key in (curses.KEY_UP, ord("k")):
            self.instrument_field_index = (self.instrument_field_index - 1) % len(self.instrument_fields)
            self.instrument_edit_buffer = ""
        elif key in (curses.KEY_DOWN, ord("j")):
            self.instrument_field_index = (self.instrument_field_index + 1) % len(self.instrument_fields)
            self.instrument_edit_buffer = ""
        elif key in (curses.KEY_LEFT, ord("h")):
            self.instrument_index = (self.instrument_index - 1) % len(INSTRUMENTS)
            self.instrument_edit_buffer = ""
        elif key in (curses.KEY_RIGHT, ord("l")):
            self.instrument_index = (self.instrument_index + 1) % len(INSTRUMENTS)
            self.instrument_edit_buffer = ""

    def move_channel_cursor(self, key):
        field_count = len(self.fields_for_current_channel())

        if key in (curses.KEY_UP, ord("k")):
            self.channel_field_index = (self.channel_field_index - 1) % field_count
            self.channel_edit_buffer = ""
        elif key in (curses.KEY_DOWN, ord("j")):
            self.channel_field_index = (self.channel_field_index + 1) % field_count
            self.channel_edit_buffer = ""
        elif key in (curses.KEY_LEFT, ord("h")):
            self.channel_index = (self.channel_index - 1) % len(CHANNELS)
            self.channel_field_index = 0
            self.channel_edit_buffer = ""
        elif key in (curses.KEY_RIGHT, ord("l")):
            self.channel_index = (self.channel_index + 1) % len(CHANNELS)
            self.channel_field_index = 0
            self.channel_edit_buffer = ""

    def edit_instrument(self, key):
        inst = self.current_instrument()
        field, kind, minimum, maximum = (
            self.instrument_fields[self.instrument_field_index]
        )

        if kind == "bool":
            if key in (ord("x"), ord("X"), ord(" ")):
                setattr(inst, field, not getattr(inst, field))
            self.engine.setup_rhythm_instruments()
            return

        if key in range(ord("0"), ord("9") + 1):
            candidate = self.instrument_edit_buffer + chr(key)

            if candidate.isdigit() and int(candidate) <= maximum:
                self.instrument_edit_buffer = (
                    candidate.lstrip("0") or "0"
                )

        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.instrument_edit_buffer = self.instrument_edit_buffer[:-1]

        elif key in (curses.KEY_ENTER, 10, 13):
            if self.instrument_edit_buffer:
                value = int(self.instrument_edit_buffer)
                setattr(
                    inst,
                    field,
                    max(minimum, min(maximum, value)),
                )
                self.instrument_edit_buffer = ""
                self.engine.setup_rhythm_instruments()

    def edit_channel(self, key):
        channel = self.current_channel()
        fields = self.fields_for_current_channel()
        field, kind, minimum, maximum = fields[self.channel_field_index]

        if kind == "bool":
            if key in (ord("x"), ord("X"), ord(" ")):
                setattr(channel, field, not getattr(channel, field))
            self.engine.setup_rhythm_channels()
            return

        if key in range(ord("0"), ord("9") + 1):
            candidate = self.channel_edit_buffer + chr(key)

            if candidate.isdigit() and int(candidate) <= maximum:
                self.channel_edit_buffer = candidate.lstrip("0") or "0"

        elif key in (curses.KEY_BACKSPACE, 127, 8):
            self.channel_edit_buffer = self.channel_edit_buffer[:-1]

        elif key in (curses.KEY_ENTER, 10, 13):
            if self.channel_edit_buffer:
                value = int(self.channel_edit_buffer)
                setattr(
                    channel,
                    field,
                    max(minimum, min(maximum, value)),
                )
                self.channel_edit_buffer = ""
                self.engine.setup_rhythm_channels()

    def run(self):
        self.last_tick = time.monotonic()
        self.engine.start()

        while True:
            self.advance_transport()
            self.draw()

            # Non-blocking input keeps the transport moving.
            self.stdscr.nodelay(True)
            key = self.stdscr.getch()

            if key == ord("q"):
                self.engine.stop()
                return

            if key == ord("s"):
                self.toggle_transport()
                continue

            if key in (ord("+"), ord("=")):
                self.set_bpm(self.state.bpm + 1)
                continue

            if key == ord("-"):
                self.set_bpm(max(1, self.state.bpm - 1))
                continue

            if key == ord("\t"):
                if self.view == "pattern":
                    self.view = "instrument"
                elif self.view == "instrument":
                    self.view = "channel"
                else:
                    self.view = "pattern"

                self.instrument_edit_buffer = ""
                self.channel_edit_buffer = ""
                continue

            if self.view == "pattern":
                self.edit_pattern(key)
            elif self.view == "instrument":
                self.move_instrument_cursor(key)
                self.edit_instrument(key)
            else:
                self.move_channel_cursor(key)
                self.edit_channel(key)

            # Avoid consuming an entire CPU core while idle.
            time.sleep(0.01)


def init_colors():
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(COLOR_ACTIVE, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_BEAT, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_CURSOR, curses.COLOR_BLACK, curses.COLOR_CYAN)
    curses.init_pair(COLOR_HEADER, curses.COLOR_BLUE, -1)
    curses.init_pair(COLOR_STATUS, curses.COLOR_BLACK, curses.COLOR_CYAN)


def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    init_colors()

    TrackerUI(stdscr).run()


if __name__ == "__main__":
    curses.wrapper(main)
