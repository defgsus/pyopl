import dataclasses
from typing import Literal

from pyopl import Channel, Operator

INSTRUMENT_TYPES = {
    "2OP": 2,
    "4OP": 4,
    "BD": 2,
    "SD": 1,
    "TT": 1,
    "CY": 1,
    "HH": 1,
}

@dataclasses.dataclass
class Instrument:
    name: str = "Instrument"
    type: Literal["2OP", "4OP", "BD", "SN", "TT", "CY", "HH"] = "2OP"
    channel_settings: tuple[Channel, Channel] = dataclasses.field(
        default_factory=lambda : (Channel(), Channel())
    )
    operators: tuple[Operator, Operator, Operator, Operator] = dataclasses.field(
        default_factory=lambda : (Operator(), Operator(), Operator(), Operator())
    )

    @property
    def num_operators(self) -> int:
        return INSTRUMENT_TYPES[self.type]

    @property
    def num_channels(self) -> int:
        return self.num_operators // 2

    @property
    def is_percussion(self) -> bool:
        return len(self.type) == 2

    @property
    def is_4op(self) -> bool:
        return self.type == "4OP"
