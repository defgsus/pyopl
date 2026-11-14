import dataclasses

from .pattern import Cell, Pattern
from .instrument import Instrument


@dataclasses.dataclass
class SongConfig:
    default_pattern_length: int = 64
    channels: int = 16
    name: str = "new song"
    bpm: int = 120
    signature: tuple[int, int] = (4, 4)


class Song:

    def __init__(self, config: SongConfig | None = None):
        from ..audio import Player
        self.config = config or SongConfig()
        self.patterns: list[Pattern] = [
            Pattern(
                channels=self.config.channels,
                length=self.config.default_pattern_length
            )
        ]
        self.instruments: list[Instrument] = [
            Instrument()
        ]
        self.player: Player = Player(self)

        pat_chan = self.patterns[0].channels[0]
        for i in range(pat_chan.length):
            if i % 4 in (0, 3):
                pat_chan.rows[i].note = 48 + i % 37

    @property
    def num_channels(self) -> int:
        return self.config.channels

    @property
    def bpm(self) -> int:
        return self.config.bpm

    @property
    def signature(self) -> tuple[int, int]:
        return self.config.signature

    def play(self):
        self.player.start()

    def stop(self):
        self.player.stop()
