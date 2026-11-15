
from rich.segment import Segment
from textual import events
from textual.app import ComposeResult, RenderResult
from textual.containers import Horizontal, Container, Vertical
from textual.strip import Strip
from textual.widget import Widget

from pyopl import *
from ..data import NOTE_OFF, Song, SongConfig, Pattern, Cell, Instrument
from .messages import InstrumentsChanged


MAX_OP_VALUES = {
    "freq_multiplier": 15,
    "output_level": 63,
    "key_scale_level": 3,
    "attack": 15,
    "decay": 15,
    "sustain": 15,
    "release": 15,
    "waveform": 7,
    "feedback": 7,
}


class OperatorsEditor(Widget):
    can_focus = True
    COMPONENT_CLASSES = [
        "op--default",
        "op--highlight",
        "op--cursor",
    ]
    DEFAULT_CSS = """
    OperatorsEditor {
        width: 1fr;
        height: 19;
        & .op--highlight {
            background: #121;
        }
        & .op--cursor {
            color: #fff;
            background: #464;
        }
    }
    """
    def __init__(self, instrument: Instrument):
        super().__init__()
        self.instrument = instrument
        self.param_names = list(vars(Operator()).keys())
        self.channel_names = list(vars(Channel()).keys())
        self.all_names = self.param_names + self.channel_names
        self.cursor_x = 0
        self.cursor_y = 0
        self.edit_value = ""

    BINDINGS = [
        ("up", "cursor_vert(-1)", "Up"),
        ("down", "cursor_vert(1)", "Down"),
        ("left", "cursor_hori(-1)", "Left"),
        ("right", "cursor_hori(1)", "Right"),
        ("pageup", "value_add(1)", "Increase"),
        ("pagedown", "value_add(-1)", "Decrease"),
    ]

    def set_instrument(self, inst: Instrument):
        self.instrument = inst
        self.cursor_x = 0
        self.cursor_y = 0
        self.refresh()

    def render_line(self, y: int) -> Strip:
        default_style = self.get_component_rich_style("op--default")
        hl_style = self.get_component_rich_style("op--highlight")
        cursor_style = self.get_component_rich_style("op--cursor")

        if not 0 <= y <= len(self.param_names) + len(self.channel_names):
            return Strip.blank(self.content_size.width, default_style)

        if self.has_focus and (y - 1) == self.cursor_y:
            default_style = hl_style

        segments = []
        if y == 0:
            segments.append(Segment(" " * 18, default_style))
            for x in range(self.instrument.num_operators):
                segments.append(Segment(
                    f"Op {x+1}  ",
                    default_style
                ))
        else:
            y -= 1
            param_name = self.all_names[y]
            segments.append(Segment(f"{param_name:<15} ", default_style))
            for x in range(self.instrument.num_operators):
                op = self.instrument.operators[x]
                ch = self.instrument.channel_settings[x//2]
                is_cursor = self.has_focus and self.cursor_x == x and self.cursor_y == y
                if y < len(self.param_names):
                    value = getattr(op, param_name)
                else:
                    value = getattr(ch, param_name)
                if isinstance(value, bool):
                    value = "X" if value else "."
                segments.append(Segment(
                    " │ " if y < len(self.param_names) or self.is_channel_column(x) else " ╎ ",
                    default_style,
                ))
                if y < len(self.param_names) or self.is_channel_column(x):
                    segments.append(Segment(f"{value:>3}", cursor_style if is_cursor else default_style))
                else:
                    segments.append(Segment(f"   ", cursor_style if is_cursor else default_style))
            segments.append(Segment(f" │", default_style))

        return Strip(segments)

    def is_channel_column(self, x: int | None = None) -> bool:
        return (self.cursor_x if x is None else x) % 2 == 0

    def num_values(self, x: int | None = None) -> int:
        num = len(self.param_names)
        if self.is_channel_column(x):
            num += len(self.channel_names)
        return num

    def get_value(self) -> int | bool:
        name = self.all_names[self.cursor_y]
        if self.cursor_y < len(self.param_names):
            op = self.instrument.operators[self.cursor_x]
            return getattr(op, name)
        else:
            ch = self.instrument.channel_settings[self.cursor_x // 2]
            return getattr(ch, name)

    def set_value(self, v: int | bool):
        name = self.all_names[self.cursor_y]
        if self.cursor_y < len(self.param_names):
            obj = self.instrument.operators[self.cursor_x]
        else:
            obj = self.instrument.channel_settings[self.cursor_x // 2]
        if not isinstance(v, bool):
            v = max(0, min(MAX_OP_VALUES[name], v))
            if len(str(v)) == len(str(MAX_OP_VALUES[name])):
                self.edit_value = ""
        setattr(obj, name, v)
        self.refresh()
        self.post_message(InstrumentsChanged())

    def action_cursor_vert(self, dir: int):
        self.cursor_y = (self.cursor_y + dir) % self.num_values()
        self.refresh()

    def action_cursor_hori(self, dir: int):
        if self.cursor_y < len(self.param_names):
            self.cursor_x = (self.cursor_x + dir) % self.instrument.num_operators
        else:
            self.cursor_x = (self.cursor_x + dir * 2) % self.instrument.num_operators
        self.refresh()

    def action_value_add(self, amt: int):
        v = self.get_value()
        if isinstance(v, bool):
            self.set_value(not v)
        else:
            self.set_value(v + amt)

    def on_mouse_down(self, event: events.MouseDown) -> None:
        o = self.content_offset
        x, y = event.x - o.x, event.y - o.y
        if 1 <= y <= len(self.all_names):
            y -= 1
            x = max(0, min(self.instrument.num_operators - 1, (x - 18) // 6))
            if y < self.num_values(x):
                self.cursor_x = x
                self.cursor_y = y
                v = self.get_value()
                if isinstance(v, bool):
                    self.set_value(not v)
                self.refresh()
                event.stop()

    def on_key(self, event: events.Key) -> None:
        name = self.all_names[self.cursor_y]
        is_int = name in MAX_OP_VALUES

        catched = False
        if event.character and "0" <= event.character <= "9" and is_int:
            self.edit_value += event.character
            val = int(self.edit_value.lstrip("0") or 0)
            self.set_value(val)
            catched = True
        else:
            self.edit_value = ""

        if not catched:
            if event.key == "space" and not is_int:
                self.set_value(not self.get_value())
                catched = True

        if catched:
            event.stop()

