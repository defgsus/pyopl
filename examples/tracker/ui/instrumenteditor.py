from textual.app import ComposeResult, RenderResult
from textual.containers import Horizontal, Container, Vertical
from textual.widgets import ListView, ListItem, Label, Input
from textual.widget import Widget

from ..data import NOTE_OFF, Song, SongConfig, Pattern, Cell, Instrument
from .operatorseditor import OperatorsEditor


class InstrumentEditor(Container):
    #can_focus = True
    def __init__(self, instrument: Instrument, **kwargs):
        super().__init__(**kwargs)
        self.instrument = instrument

    def compose(self) -> ComposeResult:
        with Vertical():
            yield Input(self.instrument.name, id="instrument-name-input")
            yield OperatorsEditor(self.instrument)

    def set_instrument(self, inst: Instrument):
        self.instrument = inst
        self.refresh()
        self.query_one("OperatorsEditor").set_instrument(inst)



class InstrumentsEditor(Container):
    #can_focus = True

    DEFAULT_CSS = """
    InstrumentEditor {
        width: 4fr;
        height: 1fr;
    }
    #instruments-list {
        width: 1fr;
        height: 1fr;
    }
    """

    def __init__(self, song: Song, **kwargs):
        super().__init__(**kwargs)
        self.song = song

    def compose(self) -> ComposeResult:
        with Horizontal():
            yield ListView(id="instruments-list")
            yield InstrumentEditor(self.song.instruments[0])

    def on_mount(self):
        list: ListView = self.query_one("#instruments-list")
        for i, inst in enumerate(self.song.instruments):
            list.append(ListItem(Label(f"{i:03d} {inst.name}")))
        list.index = 0

    def on_list_view_selected(self, message):
        if message.list_view.id == "instruments-list":
            self.query_one("InstrumentEditor").set_instrument(
                self.song.instruments[message.index]
            )

    def on_input_changed(self, message):
        if message.input.id == "instrument-name-input":
            list: ListView = self.query_one("#instruments-list")
            if item := list.highlighted_child:
                label: Label = item.query_one("Label")
                label.update(f"{list.index:03d} {message.input.value}")

