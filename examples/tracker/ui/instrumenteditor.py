from textual.app import ComposeResult, RenderResult
from textual.containers import Horizontal, Container, Vertical
from textual.widgets import ListView, ListItem, Label, Input, Select, Rule
from textual.widget import Widget

from ..data import NOTE_OFF, Song, SongConfig, Pattern, Cell, Instrument, INSTRUMENT_TYPES
from .operatorseditor import OperatorsEditor
from .messages import InstrumentsChanged


class InstrumentEditor(Container):
    #can_focus = True
    DEFAULT_CSS = """
    #instrument-name-input {
        width: 4fr;
    }
    #instrument-type-select {
        width: 1fr;
    }
    """
    def __init__(self, instrument: Instrument, **kwargs):
        super().__init__(**kwargs)
        self.instrument = instrument

    def compose(self) -> ComposeResult:
        with Vertical():
            with Horizontal():
                yield Input(self.instrument.name, id="instrument-name-input")
                yield Select(
                    [(t, t) for t in INSTRUMENT_TYPES],
                    value=self.instrument.type,
                    id="instrument-type-select"
                )
            yield OperatorsEditor(self.instrument)

    def on_select_changed(self, message: Select.Changed):
        if message.select.id == "instrument-type-select":
            self.instrument.type = message.value
            self.query_one("OperatorsEditor").set_instrument(self.instrument)
            self.post_message(InstrumentsChanged())

    def set_instrument(self, inst: Instrument):
        self.instrument = inst
        self.query_one("#instrument-type-select").value = inst.type
        self.query_one("OperatorsEditor").set_instrument(inst)
        self.refresh()



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
            yield Rule(orientation="vertical")
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

