import queue
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

    def compose(self) -> ComposeResult:
        yield Header(show_clock=False)
        yield self.editor
        yield Footer()

    def on_mount(self):
        self.timer = self.set_interval(1. / 30, self.read_player_queue, pause=True)
        self.player.start_audio()

    def read_player_queue(self):
        message = None
        while True:
            try:
                message = self.player.out_queue.get_nowait()
            except queue.Empty:
                break
        #if message is not None:
        self.editor.refresh_playback_row()

    def action_quit(self) -> None:
        self.player.stop_audio()
        self.app.exit()

    def action_play(self):
        self.player.play()
        self.timer.resume()
        #self.app.notify("Playback started")

    def action_stop(self):
        if self.player.is_playing:
            self.player.stop()
            self.timer.pause()
            self.set_timer(.1, self.editor.refresh)
        else:
            self.player.panic()
        #self.app.notify("Playback stopped")
