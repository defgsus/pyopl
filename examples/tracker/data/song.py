import dataclasses

from .pattern import Cell, Pattern


@dataclasses.dataclass
class SongConfig:
    default_pattern_length: int = 64
    channels: int = 16
    name: str = "new song"
    bpm: int = 120


class Song:

    def __init__(self, config: SongConfig | None = None):
        self.config = config or SongConfig()
        self.patterns: list[Pattern] = [
            Pattern(
                channels=self.config.channels,
                length=self.config.default_pattern_length
            )
            for _ in range(self.config.channels)
        ]

    @property
    def num_channels(self) -> int:
        return self.config.channels

    @property
    def bpm(self) -> int:
        return self.config.bpm
