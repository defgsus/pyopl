import dataclasses

from src.pyopl import Operator, Channel
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
        self.config = config or SongConfig()
        self.patterns: list[Pattern] = [
            Pattern(
                channels=self.config.channels,
                length=self.config.default_pattern_length
            )
        ]
        self.instruments: list[Instrument] = [
            Instrument(name=f"Inst {i+1}")
            for i in range(16)
        ]

        self.instruments[0].name = "Synth"
        self.instruments[0].channel_settings[0].feedback = 5

        self.instruments[1].name = "Basedrum"
        self.instruments[1].type = "BD"
        self.instruments[1].operators = (
            Operator(decay=11),
            Operator(decay=7),
            Operator(), Operator(),
        )
        self.instruments[1].channel_settings = (
            Channel(fm=True), Channel()
        )

        for i, name, type in (
                (2, "Snare", "SD"),
                (3, "Tom", "TT"),
                (4, "Cymbal", "CY"),
                (5, "HiHat", "HH"),
        ):
            self.instruments[i].name = name
            self.instruments[i].type = type
            self.instruments[i].operators = (
                Operator(decay=8, release=5),
                Operator(), Operator(), Operator()
            )


        if 0:
            pat_chan = self.patterns[0].channels[0]
            for i in range(pat_chan.length):
                if i % 4 in (0, 3):
                    pat_chan.rows[i].note = 48 + (i * 31) % 37

        pat_chan = self.patterns[0].channels[1]
        for i in range(pat_chan.length):
            if i % 8 in (0, 2):
                pat_chan.rows[i].note = 36
                pat_chan.rows[i].instrument = 1
            if i % 8 in (4, ):
                pat_chan.rows[i].note = 48
                pat_chan.rows[i].instrument = 2
            if i % 16 in (13, ):
                pat_chan.rows[i].note = 60
                pat_chan.rows[i].instrument = 3

        pat_chan = self.patterns[0].channels[2]
        for i in range(pat_chan.length):
            if i % 8 in (0, ):
                pat_chan.rows[i].note = 50
                pat_chan.rows[i].instrument = 4
            if i % 8 in (2, 4, 6):
                pat_chan.rows[i].note = 60
                pat_chan.rows[i].instrument = 5

    @property
    def num_channels(self) -> int:
        return self.config.channels

    @property
    def bpm(self) -> int:
        return self.config.bpm

    @property
    def signature(self) -> tuple[int, int]:
        return self.config.signature
