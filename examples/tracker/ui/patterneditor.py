from rich.text import Text
from rich.segment import Segment

from textual.app import App, ComposeResult, RenderResult
from textual.containers import HorizontalScroll
from textual.geometry import Region
from textual.widgets import Footer, Header, Static
from textual.widget import Widget
from textual.strip import Strip
from textual.style import Style
from textual import events

from ..audio import Player
from ..data import NOTE_OFF, Song, SongConfig, Pattern, Cell


KEYBOARD_NOTES = "ysxdcvgbhnjmq2w3er5t6z7ui9o0p"

class PatternEditor(Widget):
    can_focus = True

    COMPONENT_CLASSES = {
        "pattern--normal",
        "pattern--playback-row",
        "pattern--header",
        "pattern--header-playback-row",
        "pattern--highlight",
        "pattern--selected",
        "pattern--cursor",
        "pattern--cursor-selected",
    }

    BINDINGS = [
        ("up", "cursor_up", "Up"),
        ("down", "cursor_down", "Down"),
        ("left", "cursor_left", "Left"),
        ("right", "cursor_right", "Right"),
        ("ctrl+left", "cursor_channel_left", "Prev chan"),
        ("ctrl+right", "cursor_channel_right", "Next chan"),
        ("pageup", "cursor_page_up", "16 up"),
        ("pagedown", "cursor_page_down", "16 down"),
        ("home", "cursor_home", "Channel start"),
        ("end", "cursor_end", "Channel end"),
        ("ctrl+a", "select_all", "Select all"),
        ("ctrl+u", "unselect", "Unselect"),
        ("backspace", "backspace", "Delete value"),
        ("delete", "delete_row", "Delete row"),
        ("ctrl+delete", "delete_row(True)", "Delete row in all channels"),
        ("insert", "insert_row", "Insert row"),
        ("ctrl+insert", "insert_row(True)", "Insert row in all channels"),
        ("i", "insert_row()", "Insert row"),
        ("I", "insert_row(True)", "Insert row in all channels"),
    ]

    def __init__(self, song: Song, player: Player, **kwargs):
        super().__init__(**kwargs)
        self.song = song
        self.player = player
        self.pattern_index = 0
        self.instrument_index = 0
        self.octave = 3

        self.column_width = 15      # width of one column incl. separator
        self.num_fields = 4         # number of fields per pattern cell
        self.field_names = ["note", "inst", "vol", "fx"]
        self.x_padding = 4          # row index col
        self.y_padding = 1          # channel header
        self.y_padding_bottom = 1         # bottom row

        self.cursor_channel = 0
        self.cursor_row = 0
        self.cursor_field = 0

        self.column_offset = 0      # first viewed channel
        self.row_offset = 0         # first viewed row

        self.selection_start: tuple[tuple[int, int], int] | None = None
        self.selection_end: tuple[tuple[int, int], int] | None = None

        self._last_playback_row: int | None = None
        self._edit_value = ""       # currently typed in

    @property
    def pattern(self) -> Pattern:
        return self.song.patterns[self.pattern_index]

    @property
    def cursor_field_name(self) -> str:
        return self.field_names[self.cursor_field]

    def info_bar(self) -> list[Segment]:
        header_style = self.get_component_rich_style("pattern--header")
        sel = self.get_min_max_selection()
        if not sel:
            sel = "none"
        else:
            sel = (
                f"ch{sel[0][0] + 1}({self.field_names[sel[0][1]]})/row{sel[1]} - "
                f"ch{sel[2][0] + 1}({self.field_names[sel[2][1]]})/row{sel[3]}"
            )
        text = (
            f"pat {self.pattern_index:03d}"
            f" | ch {self.cursor_channel + 1}"
            f" | row {self.cursor_row}"
            f" | field {self.field_names[self.cursor_field]}"
            f" | oct {self.octave}"
            #f" | play-row {self.player.playback_row:03d}"
            f" | sel {sel}".ljust(self.size.width)
        )
        return [Segment(text, header_style)]

    def render_line(self, y: int):
        normal_style = self.get_component_rich_style("pattern--normal")
        play_style = self.get_component_rich_style("pattern--playback-row")
        header_style = self.get_component_rich_style("pattern--header")
        header_play_style = self.get_component_rich_style("pattern--header-playback-row")
        highlight_style = self.get_component_rich_style("pattern--highlight")
        cursor_style = self.get_component_rich_style("pattern--cursor")
        select_style = self.get_component_rich_style("pattern--selected")
        cursor_select_style = self.get_component_rich_style("pattern--cursor-selected")

        num_visible_columns = self.num_columns_visible()

        if y == 0:
            segments = [
                Segment("   |", normal_style)
            ]
            for col in range(num_visible_columns):
                if col + self.column_offset < self.pattern.num_channels:
                    segments.append(Segment(
                        f"Ch {col + self.column_offset + 1}".ljust(self.column_width - 1)
                        + "|",
                        header_style,
                    ))
            return Strip(segments)
        elif y == self.size.height - self.scroll_offset.y - self.y_padding:
            return Strip(self.info_bar())


        row = y + self.row_offset - self.y_padding
        is_row_cursor = row == self.cursor_row
        is_playback_row = self.player.is_playing and row == self.player.playback_row

        row_style = highlight_style if is_row_cursor else (
            play_style if is_playback_row
            else normal_style
        )

        is_row_selected = False
        min_max_sel = self.get_min_max_selection()
        min_x_sel, max_x_sel = None, None
        if min_max_sel:
            min_x_sel = min_max_sel[0][0] * self.num_fields + min_max_sel[0][1]
            max_x_sel = min_max_sel[2][0] * self.num_fields + min_max_sel[2][1]
            is_row_selected = min_max_sel[1] <= row <= min_max_sel[3]

        segments = [
            Segment(f"{row:03d}", header_play_style if is_playback_row else header_style),
            Segment("|", normal_style),
        ]
        for col_idx in range(num_visible_columns):
            col = col_idx + self.column_offset
            if col >= self.pattern.num_channels:
                break
            cell = self.pattern[col, row]

            is_cell_cursor = is_row_cursor and col == self.cursor_channel

            for field, text in enumerate([
                    cell.note_text, cell.instrument_text, cell.volume_text, cell.effect_text
            ]):
                x = col * self.num_fields + field
                field_style = row_style
                gap_style = row_style
                if is_row_selected:
                    if min_x_sel <= x:
                        if x <= max_x_sel:
                            field_style = select_style
                    if min_x_sel <= x < max_x_sel:
                        gap_style = select_style
                if is_cell_cursor and self.cursor_field == field:
                    field_style = cursor_select_style if field_style == select_style else cursor_style

                segments.append(Segment(text, field_style))
                if field < self.num_fields - 1:
                    segments.append(Segment(" ", gap_style))

            segments.append(Segment(
                "|",
                select_style
                if is_row_selected and min_max_sel and
                   min_x_sel <= (col * self.num_fields + self.num_fields - 1) < max_x_sel
                else row_style
            ))

        return Strip(segments)

    def pattern_row_to_screen_row(self, row: int):
        return row - self.row_offset + self.y_padding

    def refresh_pattern_row(
            self,
            pattern_row: int | None = None,
            status: bool = False
    ):
        if pattern_row is None:
            pattern_row = self.cursor_row
        y = self.pattern_row_to_screen_row(pattern_row)
        self.refresh(Region(0, y-1, self.size.width, 2))
        if status:
            self.refresh(Region(0, self.size.height-1, self.size.width, 1))

    def refresh_playback_row(self):
        row = self.player.playback_row
        if self._last_playback_row is None:
            self.refresh()
        else:
            if row < self._last_playback_row:
                self.refresh()
            elif row > self._last_playback_row:
                y = self.pattern_row_to_screen_row(self._last_playback_row)
                self.refresh(Region(0, y, self.size.width, y + row - self._last_playback_row))
        self._last_playback_row = row

    def update_selection(self):
        sel_x = (self.cursor_channel, self.cursor_field)
        sel_y = self.cursor_row
        if self.selection_start is None:
            self.selection_start = self.selection_end = (sel_x, sel_y)
        else:
            # get ordered selection rect
            min_sel_x, min_sel_y, max_sel_x, max_sel_y = self.get_min_max_selection()

            # convert x coords (col, field) to true x
            sel_x = sel_x[0] * self.num_fields + sel_x[1]
            min_sel_x = min_sel_x[0] * self.num_fields + min_sel_x[1]
            max_sel_x = max_sel_x[0] * self.num_fields + max_sel_x[1]

            # find closest corner of selection
            corners = [
                (min_sel_x, min_sel_y), # tl
                (max_sel_x, min_sel_y), # tr
                (min_sel_x, max_sel_y), # bl
                (max_sel_x, max_sel_y), # br
            ]
            min_d, min_i = None, None
            for i, (x, y) in enumerate(corners):
                d = abs(sel_x - x) + abs(sel_y - y)
                if min_d is None or d < min_d:
                    min_d, min_i = d, i
            self.app.notify(f"corner: {min_i}")

            # convert true x back to (col, field)
            sel_x = (sel_x // self.num_fields, sel_x % self.num_fields)
            min_sel_x = (min_sel_x // self.num_fields, min_sel_x % self.num_fields)
            max_sel_x = (max_sel_x // self.num_fields, max_sel_x % self.num_fields)

            # adjust the closest corner
            if min_i == 0:
                self.selection_start = (sel_x, sel_y)
                self.selection_end = (max_sel_x, max_sel_y)
            elif min_i == 1:
                self.selection_start = (min_sel_x, sel_y)
                self.selection_end = (sel_x, max_sel_y)
            elif min_i == 2:
                self.selection_start = (sel_x, min_sel_y)
                self.selection_end = (max_sel_x, sel_y)
            else:
                self.selection_start = (min_sel_x, min_sel_y)
                self.selection_end = (sel_x, sel_y)

        self.refresh()

    def get_min_max_selection(
            self
    ) -> tuple[tuple[int, int], int, tuple[int, int], int] | None:
        if self.selection_start is None or self.selection_end is None:
            return
        #if self.selection_start == self.selection_end:
        #    return
        min_sel_x = self.selection_start[0]     # (col, field)
        max_sel_x = self.selection_end[0]
        min_sel_y = self.selection_start[1]     # row
        max_sel_y = self.selection_end[1]
        if min_sel_x > max_sel_x:
            min_sel_x, max_sel_x = max_sel_x, min_sel_x
        if min_sel_y > max_sel_y:
            min_sel_y, max_sel_y = max_sel_y, min_sel_y
        return min_sel_x, min_sel_y, max_sel_x, max_sel_y

    def num_columns_visible(self, include_incomplete: bool = True) -> int:
        width = self.scrollable_size.width - self.x_padding
        if include_incomplete:
            width += self.column_width - 1
        return min(self.pattern.num_channels - 1, width // self.column_width)

    def num_rows_visible(self) -> int:
        return self.scrollable_size.height - self.y_padding - self.y_padding_bottom

    def follow_cursor(self):
        cols = self.num_columns_visible(include_incomplete=False)
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
            if self.cursor_channel == 0:
                self.cursor_field = 0
            else:
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
            if self.cursor_channel == 0:
                self.cursor_row = 0
            else:
                self.cursor_channel = 0
        self.follow_cursor()
        self.refresh()

    def action_cursor_end(self):
        if self.cursor_field < self.num_fields - 1:
            self.cursor_field = self.num_fields - 1
        else:
            if self.cursor_channel == self.pattern.num_channels - 1:
                self.cursor_row = self.pattern.length - 1
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

    def action_backspace(self):
        if self.cursor_field_name == "note":
            self.pattern[self.cursor_channel, self.cursor_row].note = None

        self.refresh()

    def action_delete_row(self, all_channels: bool = False):
        self.pattern.delete_row(self.cursor_row, None if all_channels else self.cursor_channel)
        self.refresh()

    def action_insert_row(self, all_channels: bool = False):
        self.pattern.insert_row(self.cursor_row, None if all_channels else self.cursor_channel)
        self.refresh()

    def on_key(self, event: events.Key) -> None:
        #self.app.notify(f"key {event.key}")
        catched = True
        edited_value = False
        # edit note
        if self.cursor_field_name == "note" and event.character and event.character in KEYBOARD_NOTES:
            cell = self.pattern[self.cursor_channel, self.cursor_row]
            note = KEYBOARD_NOTES.index(event.character) + 12 * self.octave
            cell.note = note
            self.action_cursor_down()
            self.player.play_cell(self.cursor_channel, cell)

        # inc/dec note
        elif self.cursor_field_name == "note" and event.character and event.character in "+-":
            cell = self.pattern[self.cursor_channel, self.cursor_row]
            if cell.note is not None and cell.note >= 0:
                if event.character == "+" and cell.note < 127 - 12:
                    cell.note += 12
                elif event.character == "-" and cell.note >= 12:
                    cell.note -= 12
                self.player.play_cell(self.cursor_channel, cell)
                self.octave = cell.note // 12
                self.refresh_pattern_row(status=True)

        # write note-off
        elif self.cursor_field_name == "note" and event.character and event.character in "^1":
            self.pattern[self.cursor_channel, self.cursor_row].note = NOTE_OFF
            self.action_cursor_down()

        # edit instrument number
        elif self.cursor_field_name == "inst" and event.character and "0" <= event.character <= "9":
            cell = self.pattern[self.cursor_channel, self.cursor_row]
            self._edit_value += event.character
            edited_value = True
            cell.instrument = min(
                int(self._edit_value.lstrip("0") or 0),
                len(self.song.instruments) - 1,
            )
            self.player.play_cell(self.cursor_channel, cell)
            self.refresh_pattern_row()

        elif event.key in ("shift+left", ):
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

        if not edited_value:
            self._edit_value = ""

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
