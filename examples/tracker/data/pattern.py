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
    def note_text(self) -> str:
        if self.note is None:
            return "..."
        if self.note == NOTE_OFF:
            return "^^^"
        return f"{NOTE_NAMES[self.note % 12]}{self.note // 12}"

    @property
    def instrument_text(self) -> str:
        return ".." if self.instrument is None else f"{self.instrument:03d}"

    @property
    def volume_text(self) -> str:
        return ".." if self.volume is None else f"{self.volume:02d}"

    @property
    def effect_text(self) -> str:
        return "..." if self.effect is None else f"{self.effect:03d}"


class PatternChannel:

    def __init__(self, length: int = 64):
        self.rows: list[Cell] = [
            Cell() for _ in range(length)
        ]

    @property
    def length(self) -> int:
        return len(self.rows)


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

    def __getitem__(self, channel_row: tuple[int, int]) -> Cell:
        return self.channels[channel_row[0]].rows[channel_row[1]]

    def __setitem__(self, channel_row: tuple[int, int], cell: Cell):
        self.channels[channel_row[0]].rows[channel_row[1]] = cell
