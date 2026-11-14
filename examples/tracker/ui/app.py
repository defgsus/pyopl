from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static
from textual.widget import Widget

from .patterneditor import PatternEditor


class TrackerApp(App):
    TITLE = "Trecker"

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
    ]

    def compose(self) -> ComposeResult:
        editor = PatternEditor(id="editor")

        yield Header(show_clock=False)
        yield Static(self.make_info_bar(editor))
        yield editor
        yield Footer()

    def make_info_bar(self, editor: PatternEditor) -> Text:
        return Text(
            f" {editor.song.config.name}"
            f" | BPM {editor.song.bpm}"
            f" | Pattern {editor.pattern_index:03d}"
            f" | Row {editor.cursor_row:03d}/{editor.pattern.length:03d}"
            f" | CH {editor.cursor_channel + 1}"
            f" | Octave {editor.octave}"
            f" | Ins {editor.instrument_index:03d}",
            style="bold",
        )

