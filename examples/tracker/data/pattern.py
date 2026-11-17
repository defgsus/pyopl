import copy
import dataclasses


NOTE_NAMES = ["C-", "C#", "D-", "D#", "E-", "F-", "F#", "G-", "G#", "A-", "A#", "B-"]
NOTE_OFF = -1

@dataclasses.dataclass
class Cell:
    note: int | None = None
    instrument: int | None = None
    volume: int | None = None
    effect: int | None = None

    @property
    def is_note_off(self) -> bool:
        return self.note == NOTE_OFF

    @property
    def has_note(self) -> bool:
        return self.note is not None and self.note >= 0

    @property
    def note_text(self) -> str:
        if self.note is None:
            return "..."
        if self.note == NOTE_OFF:
            return "^^^"
        return f"{NOTE_NAMES[self.note % 12]}{hex(self.note // 12)[2:]}"

    @property
    def instrument_text(self) -> str:
        return ".." if self.instrument is None else f"{self.instrument:02d}"

    @property
    def volume_text(self) -> str:
        return ".." if self.volume is None else f"{self.volume:02d}"

    @property
    def effect_text(self) -> str:
        return "..." if self.effect is None else f"{self.effect:03d}"

    @property
    def needs_programming(self) -> bool:
        return self.note is not None


class PatternChannel:

    def __init__(
            self,
            length: int = 64,
            num_voices: int = 1,
    ):
        self.num_voices = num_voices
        self.rows: list[Cell] = [
            Cell() for _ in range(length)
        ]

    @property
    def length(self) -> int:
        return len(self.rows)

    def delete_row(self, row: int):
        self.rows = self.rows[:row] + self.rows[row + 1:] + [Cell()]

    def insert_row(self, row: int):
        self.rows = self.rows[:row] + [Cell()] + self.rows[row:-1]


class Pattern:

    def __init__(self, channels: int = 8, length: int = 64):
        self.channels: list[PatternChannel] = [
            PatternChannel(length=length)
            for _ in range(channels)
        ]

    @property
    def length(self) -> int:
        return self.channels[0].length

    @property
    def num_channels(self) -> int:
        return len(self.channels)

    def copy(self) -> "Pattern":
        return copy.deepcopy(self)

    def copy_from(self, other: "Pattern"):
        self.channels = copy.deepcopy(other.channels)

    def __getitem__(self, channel_row: tuple[int, int]) -> Cell:
        return self.channels[channel_row[0]].rows[channel_row[1]]

    def __setitem__(self, channel_row: tuple[int, int], cell: Cell):
        self.channels[channel_row[0]].rows[channel_row[1]] = cell

    def delete_row(self, row: int, channel: int | list[int] | None = None):
        if channel is None:
            channels = range(len(self.channels))
        elif isinstance(channel, int):
            channels = [channel]
        else:
            channels = channel
        for ch in channels:
            self.channels[ch].delete_row(row)

    def insert_row(self, row: int, channel: int | list[int] | None = None):
        if channel is None:
            channels = range(len(self.channels))
        elif isinstance(channel, int):
            channels = [channel]
        else:
            channels = channel
        for ch in channels:
            self.channels[ch].insert_row(row)
