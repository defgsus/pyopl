import dataclasses
import copy

from pyopl import *

from ..data import Instrument, Song, NOTE_OFF, Cell


@dataclasses.dataclass
class PoolVoice:
    """
    One melodic voice
    """
    chip_index: int         # chip
    channel_index: int      # opl channel
    sample: int|None = None # last used sample position


@dataclasses.dataclass
class PoolChannel:
    index: int
    voices: list[PoolVoice]
    last_voice_index: int = 0
    last_instrument_index: int|None = None

    @property
    def last_voice(self) -> PoolVoice:
        return self.voices[self.last_voice_index]

    def oldest_voice_index(self) -> int:
        index, min_sample = None, None
        for i, voice in enumerate(self.voices):
            if voice.sample is None:
                return i
            if min_sample is None or voice.sample < min_sample:
                index, min_sample = i, voice.sample
        return index


ChipChannelPair = tuple[int, int]


class OPL3Pool:

    # channels for 4-op voices
    FOUR_OP_CHANNELS = [0, 1, 2, 9, 10, 11]

    # pitch channels for percussions
    PERCUSSION_CHANNELS = {
        "BD": 6,
        "SD": 7,
        "TT": 8,
        # CY & HH use 6, 7 and 8
    }

    PERCUSSION_OPERATORS = {
        "BD": (12, 15),
        "SD": (16, ),
        "TT": (14, ),
        "CY": (17, ),
        "HH": (13, ),
    }

    PERCUSSION_BITS = {
        "BD": 4,
        "SD": 3,
        "TT": 2,
        "CY": 1,
        "HH": 0,
    }

    def __init__(
            self,
            sample_rate: int,
            song: Song,
            num_perc_sets: int = 1,
            debug: bool = False,
    ):
        self.sample_rate = sample_rate
        self.song = song
        self.num_perc_sets = num_perc_sets
        self.debug = debug
        self.channels: list[PoolChannel] = []

        self.chips: list[OPL3Chip] = []
        self.channels_2op: list[ChipChannelPair] = []
        self.channels_4op: list[ChipChannelPair] = []
        self.channels_perc: list[ChipChannelPair] = []

        self._last_instrument_per_trackerchan: dict[int, Instrument] = {}
        self._programmed_instrument_per_chipchan: dict[ChipChannelPair, Instrument] = {}
        self._programmed_note_per_chipchan: dict[ChipChannelPair, tuple[int, int]] = {}
        # perc_set -> dict["BD"/"SD"/.., note]
        self._percussion_notes: dict[int, dict[str, int]] = {
            i: {}
            for i in range(self.num_perc_sets)
        }
        self._setup()

    def _setup(self):
        """
        Create as many chips as necessary and assign all voices/sets
        """
        num_2op = sum(c.polyphony for c in self.song.config.channels if c.type == "2OP")
        num_4op = sum(c.polyphony for c in self.song.config.channels if c.type == "4OP")
        num_perc = self.num_perc_sets
        while num_2op or num_4op or num_perc:
            free_channels = list(range(18))
            chip_idx = len(self.chips)

            for i in range(min(num_4op, len(self.FOUR_OP_CHANNELS))):
                ch = self.FOUR_OP_CHANNELS[i]
                self.channels_4op.append((chip_idx, ch))
                num_4op -= 1
                free_channels.remove(ch)
                free_channels.remove(ch + 3)

            if num_perc:
                for ch in self.PERCUSSION_CHANNELS.values():
                    self.channels_perc.append((chip_idx, ch))
                    free_channels.remove(ch)
                num_perc -= 1

            while num_2op and free_channels:
                self.channels_2op.append((chip_idx, free_channels.pop(0)))
                num_2op -= 1

            self.chips.append(OPL3Chip(self.sample_rate))

        channels_2op = copy.copy(self.channels_2op)
        channels_4op = copy.copy(self.channels_4op)
        for i, ch in enumerate(self.song.config.channels):
            if ch.type == "PERC":
                # TODO: not clear right now what to exactly do with polyphony for percussions
                self.channels.append(PoolChannel(
                    index=i,
                    voices=[
                        PoolVoice(chip_index=0, channel_index=6)
                    ]
                ))
                continue
            voices = []
            existing_channels = channels_2op if ch.type == "2OP" else channels_4op
            for j in range(ch.polyphony):
                chip_idx, channel_idx = existing_channels.pop(0)
                voices.append(PoolVoice(
                    chip_index=chip_idx,
                    channel_index=channel_idx,
                ))
            self.channels.append(
                PoolChannel(index=i, voices=voices)
            )

    @property
    def current_sample(self) -> int:
        return self.chips[0].current_sample

    def initialize(self):
        """
        Initialize the chips and clear states
        """
        self.delete_scheduled_writes()

        op4_regs: dict[int, int] = {
            i: 0
            for i in range(len(self.chips))
        }
        for chip_idx, ch in self.channels_4op:
            bit = self.FOUR_OP_CHANNELS.index(ch)
            op4_regs[chip_idx] |= 1 << bit

        for chip_idx, op4_reg in op4_regs.items():
            self.chips[chip_idx].write(0x104, op4_reg)

        for chip_idx, chip in enumerate(self.chips):
            # set percussion-mode per chip
            chip.write(0xBD, 0b100000 if chip_idx < self.num_perc_sets else 0)

        self._programmed_instrument_per_chipchan.clear()
        self._programmed_note_per_chipchan.clear()

    def delete_scheduled_writes(self):
        for chip in self.chips:
            chip.delete_scheduled_writes()

    def all_notes_off(self):
        for chip_idx, chip in enumerate(self.chips):
            for ch in range(18):
                chip.write(
                    reg=0xB0 + CHANNEL_REGISTERS[ch],
                    value=0,
                )
            # percussion notes off
            chip.write(0xBD, 0b100000 if chip_idx < self.num_perc_sets else 0)

    def start_program_row(self, sample: int):
        for percussions in self._percussion_notes.values():
            percussions.clear()

    def end_program_row(self, sample: int):
        for perc_set_index, percussions in self._percussion_notes.items():
            chip = self.chips[perc_set_index]
            # first send note-off to all
            reg_value = 0b100000
            chip.write(0xBD, reg_value, sample=sample)

            for perc, note in percussions.items():
                if note != NOTE_OFF:
                    reg_value |= 1 << self.PERCUSSION_BITS[perc]
                    perc_ch = self.PERCUSSION_CHANNELS.get(perc)
                    if perc_ch is not None:
                        self._note_on(
                            chip_index=perc_set_index,
                            channel=perc_ch,
                            note=note,
                            note_on=False,
                            sample=sample + 2,
                        )

            if reg_value & 0b11111:
                chip.write(0xBD, reg_value, sample=sample + 4)

    def program_cell(
            self,
            tracker_channel: int,
            cell: Cell,
            sample: int,
    ):
        pool_ch = self.channels[tracker_channel]
        voice_index = pool_ch.oldest_voice_index()
        voice = pool_ch.voices[voice_index]

        #if self.debug:
        #    print(f"programm_cell(tracker_channel={tracker_channel}, pool_ch={pool_ch.index}, voice_index={voice_index}")

        inst_index = cell.instrument
        if inst_index is None:
            inst_index = pool_ch.last_instrument_index or 0
        pool_ch.last_instrument_index = inst_index
        inst = self.song.instruments[inst_index]

        chip_chan = voice.chip_index, voice.channel_index

        if cell.has_note:
            if self._programmed_instrument_per_chipchan.get(chip_chan) != inst:
                if self.debug:
                    print(f"program_instrument(chip={chip_chan[0]}, chan={chip_chan[1]}, inst={inst_index}, sample={sample})")
                self._program_instrument(chip_chan, inst, sample)
                self._programmed_instrument_per_chipchan[chip_chan] = inst

        if inst.is_percussion:
            if cell.has_note:
                # TODO: not clear right now how to handle multiple perc-sets
                self._percussion_notes[0][inst.type] = cell.note

        else:
            if cell.note == NOTE_OFF:
                last_voice = pool_ch.last_voice
                self._note_off(last_voice.chip_index, last_voice.channel_index, sample=sample + 2)

            elif cell.note is not None:
                self._note_off(voice.chip_index, voice.channel_index, sample=sample + 2)
                self._note_on(voice.chip_index, voice.channel_index, cell.note, True, sample=sample + 4)
                pool_ch.last_voice_index = voice_index
                voice.sample = sample

    def _program_instrument(self, chip_chan: ChipChannelPair, inst: Instrument, sample: int):
        """
        Program channel and operator settings to chip.
        """
        chip, opl_ch = chip_chan
        chip = self.chips[chip]

        if inst.is_percussion:
            inst.channel_settings[0].write(chip, opl_ch, sample=sample)

            for i, op_idx in enumerate(self.PERCUSSION_OPERATORS[inst.type]):
                inst.operators[i].write(chip, op_idx, sample=sample)

        else:
            if self.debug:
                print(f"  channel_settings[0].write(chip={chip_chan[0]}, chan={opl_ch}, sample={sample})")
            inst.channel_settings[0].write(chip, opl_ch, sample=sample)
            if inst.is_4op:
                if self.debug:
                    print(f"  channel_settings[1].write(chip={chip_chan[0]}, chan={opl_ch + 3}, sample={sample})")
                inst.channel_settings[1].write(chip, opl_ch + 3, sample=sample)

            op_index = OPL3_OP_INDICES[opl_ch]

            for i, op in zip(range(inst.num_operators), inst.operators):
                if self.debug:
                    print(f"  operator[{i}].write(chip={chip_chan[0]}, index={op_index + i * 3}, sample={sample}")
                op.write(chip, index=op_index + i * 3, sample=sample)

    def _note_on(
            self,
            chip_index: int,
            channel: int,
            note: int,
            note_on: bool,
            sample: int,
    ):
        if self.debug:
            print(f"note_on(chip={chip_index}, chan={channel}, note={note}, note_on={note_on}, sample={sample})")

        chip = self.chips[chip_index]

        f_number, block = midi_note_to_f_number_and_block(note)
        self._programmed_note_per_chipchan[(chip_index, channel)] = (f_number, block)

        channel_reg = CHANNEL_REGISTERS[channel]
        chip.write(
            reg=0xA0 + channel_reg,
            value=f_number & 255,
            sample=sample,
        )
        chip.write(
            reg=0xB0 + channel_reg,
            value=(
                ((f_number >> 8) & 3)
                | (block << 2)
                | (int(note_on) << 5)
            ),
            sample=sample,
        )

    def _note_off(self, chip_index: int, channel: int, sample: int):
        if self.debug:
            print(f"note_off(chip={chip_index}, chan={channel}, sample={sample})")

        if prev := self._programmed_note_per_chipchan.get((chip_index, channel)):
            f_number, block = prev
            value = ((f_number >> 8) & 3) | (block << 2)
        else:
            value = 0

        self.chips[chip_index].write(
            reg=0xB0 + CHANNEL_REGISTERS[channel],
            value=value,
            sample=sample,
        )
