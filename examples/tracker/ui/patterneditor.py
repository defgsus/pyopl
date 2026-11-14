from rich.text import Text
from rich.segment import Segment

from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll
from textual.widgets import Footer, Header, Static
from textual.widget import Widget
from textual.strip import Strip
from textual.style import Style
from textual import events

from ..data import NOTE_OFF, Song, SongConfig, Pattern, Cell


class PatternEditor(Widget):
    can_focus = True

    COMPONENT_CLASSES = {
        "pattern--normal",
        "pattern--header",
        "pattern--highlight",
        "pattern--selected",
        "pattern--cursor",
    }

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("left", "cursor_left", "Left"),
        ("right", "cursor_right", "Right"),
        ("ctrl+left", "cursor_channel_left", "Left"),
        ("ctrl+right", "cursor_channel_right", "Right"),
        ("pageup", "cursor_page_up", "16 up"),
        ("pagedown", "cursor_page_down", "16 down"),
        ("home", "cursor_home", "Channel start"),
        ("end", "cursor_end", "Channel end"),
        ("ctrl+a", "select_all", "Select all"),
        ("ctrl+u", "unselect", "Unselect"),
    ]

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.song = Song()
        self.pattern_index = 0
        self.instrument_index = 0
        self.octave = 3

        self.column_width = 14      # width of one column incl. separator
        self.num_fields = 4         # number of fields per pattern cell
        self.field_names = ["note", "inst", "vol", "fx"]
        self.x_padding = 4          # row index col
        self.y_padding = 1          # channel header

        self.cursor_channel = 0
        self.cursor_row = 0
        self.cursor_field = 0

        self.column_offset = 0      # first viewed channel
        self.row_offset = 0         # first viewed row

        self.selection_start: tuple[tuple[int, int], int] | None = None
        self.selection_end: tuple[tuple[int, int], int] | None = None

    @property
    def pattern(self) -> Pattern:
        return self.song.patterns[self.pattern_index]

    def render_line(self, y: int):
        normal_style = self.get_component_rich_style("pattern--normal")
        header_style = self.get_component_rich_style("pattern--header")
        highlight_style = self.get_component_rich_style("pattern--highlight")
        cursor_style = self.get_component_rich_style("pattern--cursor")
        select_style = self.get_component_rich_style("pattern--selected")

        num_visible_columns = self.num_columns_visible()

        if y == 0:
            segments = [
                Segment("   |", normal_style)
            ]
            for col in range(self.num_columns_visible()):
                segments.append(Segment(
                    f"Ch {col + self.column_offset + 1}".ljust(self.column_width - 1)
                    + ("|" if col < num_visible_columns - 1 else ""),
                    header_style,
                ))
            return Strip(segments)
        elif y == self.size.height - self.scroll_offset.y - self.y_padding:
            sel = self.get_min_max_selection()
            if not sel:
                sel = "none"
            else:
                sel = (
                    f"ch{sel[0][0]}:{self.field_names[sel[0][1]]}/row{sel[1] + 1} - "
                    f"ch{sel[2][0]}:{self.field_names[sel[2][1]]}/row{sel[3] + 1}"
                )
            text = (
                f"ch {self.cursor_channel + 1}"
                f" | row {self.cursor_row}"
                f" | field {self.cursor_field}"
                f" | sel {sel}".ljust(self.size.width)
            )
            return Strip([Segment(text, header_style)])

        row = y + self.row_offset - self.y_padding
        is_row_cursor = row == self.cursor_row
        row_style = highlight_style if is_row_cursor else normal_style

        is_row_selected = False
        min_max_sel = self.get_min_max_selection()
        min_x_sel, max_x_sel = None, None
        if min_max_sel:
            min_x_sel = min_max_sel[0][0] * self.num_fields + min_max_sel[0][1]
            max_x_sel = min_max_sel[2][0] * self.num_fields + min_max_sel[2][1]
            is_row_selected = min_max_sel[1] <= row <= min_max_sel[3]

        segments = [
            Segment(f"{row:03d}", header_style),
            Segment("|", normal_style),
        ]
        for col_idx in range(num_visible_columns):
            col = col_idx + self.column_offset
            cell = self.pattern[col, row]

            is_cell_cursor = is_row_cursor and col == self.cursor_channel

            for field, text in enumerate([
                    cell.note_text, cell.instrument_text, cell.volume_text, cell.effect_text
            ]):
                x = col * self.num_fields + field
                field_style = row_style
                gap_style = row_style
                if is_cell_cursor and self.cursor_field == field:
                    field_style = cursor_style
                elif is_row_selected:
                    if min_x_sel <= x:
                        if x <= max_x_sel:
                            field_style = select_style
                if is_row_selected and min_x_sel <= x < max_x_sel:
                    gap_style = select_style

                segments.append(Segment(text, field_style))
                if field < self.num_fields - 1:
                    segments.append(Segment(" ", gap_style))

            if col_idx < num_visible_columns - 1:
                segments.append(Segment(
                    "|",
                    select_style
                    if is_row_selected and min_max_sel and
                       min_x_sel <= (col * self.num_fields + self.num_fields - 1) < max_x_sel
                    else row_style
                ))

        return Strip(segments)

    def update_selection(self):
        sel = ((self.cursor_channel, self.cursor_field), self.cursor_row)
        if self.selection_start is None:
            self.selection_start = self.selection_end = sel
        else:
            #min_sel_x, min_sel_y, max_sel_x, max_sel_y = self.get_min_max_selection()
            d_start = (
                abs(sel[0][0] - self.selection_start[0][0])
                + abs(sel[1] - self.selection_start[1])
            )
            d_end = (
                abs(sel[0][0] - self.selection_end[0][0])
                + abs(sel[1] - self.selection_end[1])
            )
            if d_start <= d_end:
                self.selection_start = sel
            else:
                self.selection_end = sel
        self.refresh()

    def get_min_max_selection(
            self
    ) -> tuple[tuple[int, int], int, tuple[int, int], int] | None:
        if self.selection_start is None or self.selection_end is None:
            return
        if self.selection_start == self.selection_end:
            return
        min_sel_x = self.selection_start[0]     # (col, field)
        max_sel_x = self.selection_end[0]
        min_sel_y = self.selection_start[1]     # row
        max_sel_y = self.selection_end[1]
        if min_sel_x > max_sel_x:
            min_sel_x, max_sel_x = max_sel_x, min_sel_x
        if min_sel_y > max_sel_y:
            min_sel_y, max_sel_y = max_sel_y, min_sel_y
        return min_sel_x, min_sel_y, max_sel_x, max_sel_y

    def num_columns_visible(self) -> int:
        return (self.scrollable_size.width - self.x_padding) // self.column_width

    def num_rows_visible(self) -> int:
        return self.scrollable_size.height - self.y_padding

    def follow_cursor(self):
        cols = self.num_columns_visible()
        rows = self.num_rows_visible()

        s_x, s_y = self.column_offset, self.row_offset
        if self.cursor_channel < s_x:
            s_x = min(s_x, self.cursor_channel)
        if self.cursor_channel >= s_x + cols - 1:
            s_x = max(s_x, self.cursor_channel - cols + 1)
        if self.cursor_row < s_y:
            s_y = min(s_y, self.cursor_row)
        if self.cursor_row >= s_y + rows - 1:
            s_y = max(s_y, self.cursor_row - rows + 1)

        if s_x != self.column_offset or s_y != self.row_offset:
            self.column_offset = s_x
            self.row_offset = s_y
            self.refresh()

    def action_cursor_left(self):
        self.cursor_field -= 1
        if self.cursor_field < 0:
            self.cursor_field = self.num_fields - 1
            self.cursor_channel = max(self.cursor_channel - 1, 0)
        self.follow_cursor()
        self.refresh()

    def action_cursor_right(self):
        self.cursor_field += 1
        if self.cursor_field >= self.num_fields:
            if self.cursor_channel == self.pattern.num_channels - 1:
                self.cursor_field = self.num_fields - 1
            else:
                self.cursor_field = 0
                self.cursor_channel = min(self.cursor_channel + 1, self.pattern.num_channels - 1)
        self.follow_cursor()
        self.refresh()

    def action_cursor_up(self, steps: int = 1):
        self.cursor_row = max(self.cursor_row - steps, 0)
        self.follow_cursor()
        self.refresh()

    def action_cursor_down(self, steps: int = 1):
        self.cursor_row = min(self.cursor_row + steps, self.pattern.length - 1)
        self.follow_cursor()
        self.refresh()

    def action_cursor_channel_left(self):
        self.cursor_channel = max(self.cursor_channel - 1, 0)
        self.follow_cursor()
        self.refresh()

    def action_cursor_channel_right(self):
        self.cursor_channel = min(self.cursor_channel + 1, self.pattern.num_channels - 1)
        self.follow_cursor()
        self.refresh()

    def action_cursor_page_up(self):
        self.action_cursor_up(16)

    def action_cursor_page_down(self):
        self.action_cursor_down(16)

    def action_cursor_home(self):
        if self.cursor_field > 0:
            self.cursor_field = 0
        else:
            self.cursor_channel = 0
        self.follow_cursor()
        self.refresh()

    def action_cursor_end(self):
        if self.cursor_field < self.num_fields - 1:
            self.cursor_field = self.num_fields - 1
        else:
            self.cursor_channel = self.pattern.num_channels - 1
        self.follow_cursor()
        self.refresh()

    def action_select_all(self):
        if not self.selection_start:
            # select current col * 16
            row_start = (self.cursor_row // 16) * 16
            self.selection_start = ((self.cursor_channel, 0), row_start)
            self.selection_end = ((self.cursor_channel, self.num_fields - 1), row_start + 15)
        else:
            min_sel_x, min_sel_y, max_sel_x, max_sel_y = self.get_min_max_selection()
            # expand current channel to full
            if (
                    min_sel_x[0] == self.cursor_channel and max_sel_x[0] == self.cursor_channel
            ):
                new_min = (min_sel_x, 0)
                new_max = (max_sel_x, self.pattern.length - 1)
                # expand from full channel to all
                if (min_sel_x, min_sel_y) == new_min and (max_sel_x, max_sel_y) == new_max:
                    self.selection_start = ((0, 0), 0)
                    self.selection_end = ((self.pattern.num_channels - 1, self.num_fields - 1), self.pattern.length - 1)
                else:
                    self.selection_start = new_min
                    self.selection_end = new_max
            else:
                new_min = ((0, 0), 0)
                new_max = ((self.pattern.num_channels - 1, self.num_fields - 1), self.pattern.length - 1)
                # unselect if all is selected
                if (min_sel_x, min_sel_y) == new_min and (max_sel_x, max_sel_y) == new_max:
                    self.selection_start = self.selection_end = None
                else:
                    self.selection_start, self.selection_end = new_min, new_max
        self.refresh()

    def action_unselect(self):
        self.selection_start = self.selection_end = None
        self.refresh()

    def on_key(self, event: events.Key) -> None:
        catched = True
        if event.key in ("shift+left", ):
            self.update_selection()
            self.action_cursor_left()
            self.update_selection()
        elif event.key in ("shift+right", ):
            self.update_selection()
            self.action_cursor_right()
            self.update_selection()
        elif event.key in ("shift+up", "ctrl+up"):
            self.update_selection()
            self.action_cursor_up()
            self.update_selection()
        elif event.key in ("shift+down", "ctrl+down"):
            self.update_selection()
            self.action_cursor_down()
            self.update_selection()
        else:
            catched = False

        if catched:
            event.stop()

    def on_mouse_down(self, event: events.MouseDown) -> None:
        o = self.content_offset
        self.cursor_channel = (event.x - o.x - self.x_padding) // self.column_width
        self.cursor_row = event.y - o.y - self.y_padding
        self.refresh()
        event.stop()

    def on_mouse_scroll_up(self, event: events.MouseScrollDown) -> None:
        self.cursor_row = max(self.cursor_row - 5, 0)
        self.follow_cursor()
        self.refresh()
        event.stop()

    def on_mouse_scroll_down(self, event: events.MouseScrollDown) -> None:
        self.cursor_row = min(self.cursor_row + 5, self.pattern.length - 1)
        self.follow_cursor()
        self.refresh()
        event.stop()

    def on_mouse_scroll_left(self, event: events.MouseScrollDown) -> None:
        self.cursor_channel = max(self.cursor_channel - 3, 0)
        self.follow_cursor()
        self.refresh()
        event.stop()

    def on_mouse_scroll_right(self, event: events.MouseScrollDown) -> None:
        self.cursor_channel = min(self.cursor_channel + 3, self.pattern.num_channels - 1)
        self.follow_cursor()
        self.refresh()
        event.stop()
