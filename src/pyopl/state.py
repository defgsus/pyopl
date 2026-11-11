import dataclasses

from pyopl import OPL3Chip, midi_note_to_f_number_and_block


# operator index -> register offset
OP_REGISTERS = [
    0x000,0x001,0x002,0x003,0x004,0x005,
    0x008,0x009,0x00A,0x00B,0x00C,0x00D,
    0x010,0x011,0x012,0x013,0x014,0x015,
    0x100,0x101,0x102,0x103,0x104,0x105,
    0x108,0x109,0x10A,0x10B,0x10C,0x10D,
    0x110,0x111,0x112,0x113,0x114,0x115,
]

# channel index -> register offset
CHANNEL_REGISTERS = [
    0x000,0x001,0x002,0x003,0x004,0x005,0x006,0x007,0x008,
    0x100,0x101,0x102,0x103,0x104,0x105,0x106,0x107,0x108,
]

# channel -> operator index (in OPL2 mode)
OPL2_OP_INDICES = [
    0, 1, 2, 8, 9, 10, 16, 17, 18
]

# channel -> operator index
OPL3_OP_INDICES = [
    0,  1,  2,   6,  7,  8,  12, 13, 14,
    18, 19, 20,  24, 25, 26,  30, 31, 32,
]


class Waveform:
    Sine = 0
    HalfSine = 1
    AbsSine = 2
    PulseSine = 3
    EvenSine = 4
    EvenAbsSine = 5
    Square = 6
    Pulse = 7


@dataclasses.dataclass
class Channel:
    """
    Settings for a channel (0-17)
    """
    fm: bool = False
    feedback: int = 0   # 0-7
    left: bool = True
    right: bool = True

    def write(self, chip: OPL3Chip, channel: int, sample: int = 0):
        """
        Write the channel state to the chip.

        :param chip: OPL3Chip instance
        :param channel: int, [0, 17]
        :param sample: int, optional absolute sample position to execute register write
        """
        chip.write(
            0xC0 + CHANNEL_REGISTERS[channel],
            int(not self.fm)
            | ((self.feedback & 7) << 1)
            | (int(self.left) << 4)
            | (int(self.right) << 5),
            sample=sample,
        )


@dataclasses.dataclass
class Operator:
    """
    Settings for an operator (0-35)
    """
    freq_multiplier: int = 1    # 0-15
    ksr: bool = False
    sustain: bool = False
    vibrato: bool = False
    tremolo: bool = False
    output_level: int = 63      # 0 - 63
    key_scale_level: int = 1    # 0 - 3
    attack: int = 15            # 0 - 15
    decay: int = 0              # 0 - 15
    sustain_level: int = 15     # 0 - 15
    release: int = 5            # 0 - 15
    waveform: int = 0           # 0 - 7

    def write(self, chip: OPL3Chip, index: int, sample: int = 0):
        """
        Write the operator state to the chip.

        :param chip: OPL3Chip instance
        :param index: int, Operator index [0, 35]. Note that depending on the chip's opl3 flag,
            the index number must be mapped via `OPL2_OP_INDICES` or `OPL3_OP_INDICES`.
        :param sample: int, optional absolute sample position to execute register write
        """
        reg_index = OP_REGISTERS[index]
        chip.write(
            0x20 + reg_index,
            (self.freq_multiplier & 7)
            | (int(self.ksr) << 4)
            | (int(self.sustain) << 5)
            | (int(self.vibrato) << 6)
            | (int(self.tremolo) << 7),
            sample=sample,
            )
        chip.write(
            0x40 + reg_index,
            (63 - (self.output_level & 63))
            | ((self.key_scale_level & 3) << 6),
            sample=sample,
            )
        chip.write(
            0x60 + reg_index,
            (self.decay & 15)
            | ((self.attack & 15) << 4),
            sample=sample,
            )
        chip.write(
            0x80 + reg_index,
            (self.release & 15)
            | ((self.sustain_level & 15) << 4),
            sample=sample,
            )
        chip.write(
            0xE0 + reg_index,
            (self.waveform & 7),
            sample=sample,
            )


class OPL3State:
    """
    Convenience wrapper around an OPL3Chip.

    Supports writing global, channel-wise and operator-wise settings.
    """
    def __init__(self, chip: OPL3Chip):
        self.chip = chip
        self._notes: list[tuple[int, int] | None] = [None] * 18

    @property
    def opl3(self) -> bool:
        return self.chip.opl3

    def set_opl3(self, enable: bool = True, sample: int = 0):
        self.chip.write(0x105, int(enable), sample=sample)

    def set_rythm_mode(self, enable: bool = True, sample: int = 0):
        self.chip.write(
            0xBD,
            0b100000 if enable else 0,
            sample=sample,
        )

    def set_4_ops(
            self,
            ch0: bool = False,
            ch1: bool = False,
            ch2: bool = False,
            ch9: bool = False,
            ch10: bool = False,
            ch11: bool = False,
            sample: int = 0,
    ):
        self.chip.write(
            reg=0x104,
            value=(
                    int(ch0)
                    | (int(ch1) << 1)
                    | (int(ch2) << 2)
                    | (int(ch9) << 3)
                    | (int(ch10) << 4)
                    | (int(ch11) << 5)
            ),
            sample=sample,
        )

    def midi_note_on(
            self,
            channel: int,
            note: int,
            sample: int = 0,
            a4: float = 440.,
    ):
        f_number, block = midi_note_to_f_number_and_block(note, a4=a4)
        self.note_on(
            channel=channel,
            f_number=f_number,
            block=block,
            sample=sample,
        )

    def note_on(
            self,
            channel: int,
            f_number: int,
            block: int,
            sample: int = 0,
    ):
        channel_reg = CHANNEL_REGISTERS[channel]
        self._notes[channel] = (f_number, block)
        self.chip.write(
            reg=0xA0 + channel_reg,
            value=f_number & 255,
            sample=sample,
        )
        self.chip.write(
            reg=0xB0 + channel_reg,
            value=((f_number >> 8) & 3)
                  | (block << 2)
                  | 0b100000,
            sample=sample,
        )

    def note_off(self, channel: int, sample: int = 0):
        if prev := self._notes[channel]:
            f_number, block = prev
            # clear note-on bit, keep f_number and block the same
            value = ((f_number >> 8) & 3) | (block << 2)
        else:
            value = 0
        self.chip.write(
            reg=0xB0 + CHANNEL_REGISTERS[channel],
            value=value,
            sample=sample,
        )

    def write_channel(
            self,
            channel: int,
            ch: Channel,
            sample: int = 0,
    ):
        ch.write(self.chip, channel, sample=sample)

    def write_operators(self, channel: int, *operators: Operator, sample: int = 0):
        if self.opl3:
            op_index = OPL3_OP_INDICES[channel]
        else:
            op_index = OPL2_OP_INDICES[channel]

        for i, op in enumerate(operators):
            op.write(self.chip, index=op_index + i * 3, sample=sample)
