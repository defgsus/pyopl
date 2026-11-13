import curses
import dataclasses
import textwrap
import time

from pyopl import *


# Color pair IDs
COLOR_NORMAL = 1
COLOR_ACTIVE = 2
COLOR_INACTIVE = 3
COLOR_SELECTED = 4

@dataclasses.dataclass
class Global:
    note: int = 48
    op4: bool = False
    tremolo_depth: bool = False
    vibrato_depth: bool = False
    #composite_sine_wave: bool = False
    #note_sel: bool = False

MAX_VALUES = {
    "op.freq_multiplier": 15,
    "op.output_level": 63,
    "op.key_scale_level": 3,
    "op.attack": 15,
    "op.decay": 15,
    "op.sustain_level": 15,
    "op.release": 15,
    "op.waveform": 7,
    "ch.feedback": 7,
    "gl.note": 127,
}


class SoundEditor:

    def __init__(self, stdsrc):
        self.stdscr = stdsrc
        self.operators = [
            Operator()
            for _ in range(4)
        ]
        self.channels = [
            Channel()
            for _ in range(2)
        ]
        self.global_config = Global()
        self.edit_modes = ["op1", "op2", "op3", "op4", "ch1", "ch2", "gl1"]
        self.edit_mode = self.edit_modes[0]
        self.edit_row = 0
        self.edit_value = ""
        self.chip = OPL3Chip()
        self.state = OPL3State(self.chip)
        self.is_note_on = False
        for what in self.edit_modes:
            self.update_chip(what)
        self.audio = AudioStream(self.chip)
        self.audio.start()
        self._last_size = height, width = self.stdscr.getmaxyx()

    def draw(self):
        height, width = self.stdscr.getmaxyx()
        if (height, width) != self._last_size:
            self._last_size = (height, width)
            self.stdscr.erase()

        for i in range(len(self.operators)):
            self.draw_thing(i * 25, 0, "op", i)
        for i in range(len(self.channels)):
            self.draw_thing(i * 25, 14, "ch", i)
        self.draw_thing(0, 20, "gl", 0)

        diagram = self.get_diagram()
        if diagram:
            lines = [line for line in textwrap.dedent(diagram).splitlines() if line.strip()]
            lines += [""] * (11 - len(lines))
            for i, line in enumerate(lines):
                try:
                    self.stdscr.addstr(
                        14 + i, 50,
                        line.ljust(50)
                    )
                except curses.error:
                    break

        # --- bottom lines ---
        obj = self.current_object()
        param_name = type(obj).__name__
        if not isinstance(obj, Global):
            param_name = f"{param_name} {self.edit_mode[2:]}"
        value_names = list(vars(obj).keys())
        value_name = value_names[self.edit_row]
        if max_value := MAX_VALUES.get(f"{self.edit_mode[:2]}.{value_name}"):
            value_name = f"{value_name}: 0-{max_value}"
        else:
            value_name = f"{value_name}: yes/no"

        self.stdscr.addstr(
            height - 2, 0,
            f"{param_name}: {value_name}".ljust(40)
        )
        self.stdscr.addstr(
            height - 1, 0,
            f"Up/Dn: change row"
            f" | Lf/Rt/Sp/0-9: change value"
            f" | (Shift+)Tab: change object"
            f" | p: play"
            f" | o: note off"
        )

    def draw_thing(self, x: int, y: int, what: str, index: int):
        if what == "op":
            thing = self.operators[index]
            name = f"Operator {index+1}"
        elif what == "ch":
            thing = self.channels[index]
            name = f"Channel {index+1}"
        elif what == "gl":
            thing = self.global_config
            name = "Global"
        else:
            return

        is_used = f"{what}{index+1}" in self.active_edit_modes()
        if not is_used:
            name = f"{name} (inactive)"

        is_active = self.edit_mode == f"{what}{index+1}"
        color = curses.color_pair(
            COLOR_INACTIVE if not is_used else
            (COLOR_ACTIVE if is_active else COLOR_NORMAL)
        )

        self.stdscr.addstr(
            y, x,
            name.ljust(22),
            color | (curses.A_BOLD if is_used else 0) | curses.A_ITALIC
        )
        for i, (key, value) in enumerate(vars(thing).items()):
            is_selected = is_active and i == self.edit_row
            row_color = curses.color_pair(COLOR_SELECTED) if is_selected else color
            self.stdscr.addstr(
                y + i + 1, x,
                key,
                color
            )
            if isinstance(value, bool):
                value = "yes" if value else "no"

            self.stdscr.addstr(
                y + i + 1, x + 19,
                f"{str(value):>3}",
                row_color
            )

    def get_diagram(self):
        if not self.global_config.op4:
            if self.channels[0].fm:
                return """
                +-----+   +-----+
                | Op1 |-->+ Op2 |--> Output
                +-----+   +-----+
                """
            else:
                return """
                +-----+
                | Op1 |--+
                +-----+  |
                         +-----> Output
                +-----+  |
                | Op2 |--+
                +-----+      
                """
        else:
            if self.channels[0].fm:
                if self.channels[1].fm:
                    return """
                    +-----+   +-----+   +-----+   +-----+
                    | Op1 |-->+ Op2 |-->| Op3 |-->+ Op4 |--> Output
                    +-----+   +-----+   +-----+   +-----+
                    """
                else:
                    return """
                    +-----+   +-----+
                    | Op1 |-->+ Op2 |--+ 
                    +-----+   +-----+  |
                                       +--> Output
                    +-----+   +-----+  |
                    | Op3 |-->+ Op4 |--+ 
                    +-----+   +-----+
                    """
            else:
                if self.channels[1].fm:
                    return """
                    +-----+
                    | Op1 |----------------------+
                    +-----+                      |
                                                 +--> Output
                    +-----+   +-----+   +-----+  |
                    | Op2 |-->| Op3 |-->| Op4 |--+
                    +-----+   +-----+   +-----+
                    """
                else:
                    return """
                    +-----+
                    | Op1 |------------+
                    +-----+            |
                                       |
                    +-----+   +-----+  |
                    | Op2 |-->| Op3 |--+--> Output
                    +-----+   +-----+  |
                                       |
                    +-----+            |
                    | Op4 |------------+
                    +-----+              
                    """

    def active_edit_modes(self) -> list[str]:
        if self.global_config.op4:
            return self.edit_modes
        return [
            m for m in self.edit_modes
            if m not in ("op3", "op4", "ch2")
        ]

    def change_edit_mode(self, direction: int):
        active_modes = self.active_edit_modes()
        self.edit_mode = self.edit_modes[
            (self.edit_modes.index(self.edit_mode) + direction) % len(self.edit_modes)
        ]
        if direction == 0:
            direction = 1
        while self.edit_mode not in active_modes:
            self.edit_mode = self.edit_modes[
                (self.edit_modes.index(self.edit_mode) + direction) % len(self.edit_modes)
            ]

    def get_object(self, what: str) -> tuple[Operator|Channel|Global, int]:
        index = int(what[2:]) - 1
        if what.startswith("op"):
            return self.operators[index], index
        elif what.startswith("ch"):
            return self.channels[index], index
        elif what.startswith("gl"):
            return self.global_config, index
        else:
            raise NotImplementedError

    def current_object(self) -> Operator|Channel|Global:
        obj, idx = self.get_object(self.edit_mode)
        return obj

    def get_value(self):
        values = list(vars(self.current_object()).values())
        return values[self.edit_row]

    def max_value(self) -> int|None:
        values = list(vars(self.current_object()).items())
        value_name = values[self.edit_row][0]
        return MAX_VALUES.get(f"{self.edit_mode[:2]}.{value_name}")

    def set_value(self, value: bool|int):
        obj = self.current_object()
        values = list(vars(obj).items())
        value_name = values[self.edit_row][0]
        if isinstance(value, bool):
            new_value = value
        elif isinstance(value, int):
            new_value = max(0, min(
                MAX_VALUES[f"{self.edit_mode[:2]}.{value_name}"],
                value
            ))
        else:
            return
        setattr(obj, value_name, new_value)
        self.update_chip(self.edit_mode)

    def update_chip(self, what: str):
        obj, index = self.get_object(what)
        if isinstance(obj, Operator):
            self.state.write_operators(0, *[
                op if i == index else None
                for i, op in enumerate(self.operators)
            ])
        elif isinstance(obj, Channel):
            self.state.write_channel(index * 3, obj)
        elif isinstance(obj, Global):
            self.state.set_4_ops(ch0=obj.op4)
            self.state.set_tremolo_vibrato_depth(obj.tremolo_depth, obj.vibrato_depth)
            self.state.midi_note_on(0, obj.note, note_on=self.is_note_on)
            #self.chip.write(
            #    0x08,
            #    (int(self.global_config.composite_sine_wave) << 7)
            #    | (int(self.global_config.note_sel << 6))
            #)

    def play(self):
        cs = self.chip.current_sample
        if self.is_note_on:
            self.state.note_off(0, sample=cs)
        self.state.midi_note_on(0, self.global_config.note, sample=cs + 2)
        self.is_note_on = True

    def note_off(self):
        if self.is_note_on:
            self.state.midi_note_on(0, self.global_config.note, note_on=False)
            self.is_note_on = False

    def run(self):
        while True:
            max_row = len(vars(self.current_object()))
            self.edit_row = min(max_row - 1, self.edit_row)
            self.draw()

            self.stdscr.nodelay(True)
            key = self.stdscr.getch()

            if key in (ord("q"), 27):
                self.audio.stop()
                return

            if key == ord("p"):
                self.play()
            elif key == ord("o"):
                self.note_off()
            elif key == curses.KEY_DOWN:
                self.edit_row = (self.edit_row + 1) % max_row
            elif key == curses.KEY_UP:
                self.edit_row = (self.edit_row - 1) % max_row
            elif key in (9, 353):
                direction = 1 if key == 9 else -1
                self.change_edit_mode(direction)

            elif key in (curses.KEY_LEFT, curses.KEY_RIGHT):
                val = self.get_value()
                if isinstance(val, bool):
                    val = not val
                else:
                    val += 1 if key == curses.KEY_RIGHT else -1
                self.set_value(val)
            elif key == ord(" "):
                val = self.get_value()
                if isinstance(val, bool):
                    self.set_value(not val)

            if ord("0") <= key <= ord("9"):
                if not isinstance(self.get_value(), bool):
                    self.edit_value += chr(key)
                    try:
                        val = int(self.edit_value.lstrip("0") or 0)
                        self.set_value(val)
                        if len(str(self.get_value())) == len(str(self.max_value())):
                            self.edit_value = ""
                    except ValueError:
                        pass
            elif key > 0:
                self.edit_value = ""

            time.sleep(0.01)

def main(stdscr):
    curses.curs_set(0)
    stdscr.keypad(True)
    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(COLOR_NORMAL, curses.COLOR_CYAN, -1)
    curses.init_pair(COLOR_ACTIVE, curses.COLOR_GREEN, -1)
    curses.init_pair(COLOR_INACTIVE, curses.COLOR_WHITE, -1)
    curses.init_pair(COLOR_SELECTED, curses.COLOR_BLACK, curses.COLOR_GREEN)

    SoundEditor(stdscr).run()


if __name__ == "__main__":
    curses.wrapper(main)
