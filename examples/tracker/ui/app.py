from functools import partial

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static
from textual.widget import Widget

from .patterneditor import PatternEditor
from ..audio import Player
from ..data import Song

class TrackerApp(App):
    TITLE = "Trecker"

    CSS_PATH = "app.tcss"

    BINDINGS = [
        ("ctrl+q", "quit", "Quit"),
        ("f7", "play", "Start playback"),
        ("f8", "stop", "Stop playback"),
    ]

    def __init__(self):
        super().__init__()
        self.song = Song()
        self.player = Player(self.song)
        self.editor = PatternEditor(song=self.song, player=self.player, id="editor")
        self.player.set_row_callback(partial(self.call_from_thread, self.player_row_changed))

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield self.editor
        yield Footer()

    def player_row_changed(self):
        #import threading
        #self.app.notify(f"{threading.current_thread()}: row={self.player.playback_row}")
        self.editor.refresh_row(self.player.playback_row)

    def action_quit(self) -> None:
        self.player.stop()
        self.app.exit()

    def action_play(self):
        self.player.start()
        self.app.notify("Playback started")

    def action_stop(self):
        self.player.stop()
        self.app.notify("Playback stopped")
