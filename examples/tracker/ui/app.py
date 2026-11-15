import queue
from functools import partial

from rich.text import Text
from textual.app import App, ComposeResult
from textual.widgets import Footer, Header, Static, TabbedContent
from textual.widget import Widget

from .instrumenteditor import InstrumentsEditor
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

    def compose(self) -> ComposeResult:
        # yield Header(show_clock=False)
        with TabbedContent("patterns", "instruments"):
            yield self.editor
            yield InstrumentsEditor(self.song)
        yield Footer()

    def on_mount(self):
        self.query_one("PatternEditor").focus()
        self.timer_play = self.set_interval(1. / 30, self.editor.refresh_playback_row, pause=True)
        self.timer_queue = self.set_interval(1. / 30, self.read_player_queue, pause=True)
        self.player.start_audio()

    def read_player_queue(self):
        while True:
            try:
                message = self.player.out_queue.get_nowait()
                if message:
                    if msg := message.get("exception"):
                        self.app.notify(msg, severity="error")
            except queue.Empty:
                break

    def action_quit(self) -> None:
        self.player.stop_audio()
        self.app.exit()

    def action_play(self):
        self.player.play()
        self.timer_play.resume()
        #self.app.notify("Playback started")

    def action_stop(self):
        if self.player.is_playing:
            self.player.stop()
            self.timer_play.pause()
            self.set_timer(.1, self.editor.refresh)
        else:
            self.player.panic()
        #self.app.notify("Playback stopped")

    def on_instruments_changed(self, message):
        self.player.update_instruments()
