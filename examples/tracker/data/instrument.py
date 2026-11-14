import dataclasses

from pyopl import Channel, Operator


@dataclasses.dataclass
class Instrument:
    name: str = "Instrument"
    channel_settings: Channel = dataclasses.field(default_factory=lambda : Channel())
    operators: tuple[Operator] = dataclasses.field(default_factory=lambda : (Operator(), Operator()))


