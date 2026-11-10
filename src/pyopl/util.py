import math

OPL_REFERENCE_RATE = 49716.0
FNUMBER_MAX = 1023


def frequency_to_f_number_and_block(frequency: float) -> tuple[int, int]:
    """
    Convert a frequency in Hz to an OPL F-number and block.

    Returns:
        (f_number, block)
    """
    # Choose the smallest block that keeps F-number within 0..1023.
    minimum_block = math.log2(
        frequency * (2 ** 20) / (OPL_REFERENCE_RATE * FNUMBER_MAX)
    )
    block = max(0, min(7, math.ceil(minimum_block)))

    f_number = max(0, min(FNUMBER_MAX, round(frequency * (2 ** (20 - block)) / OPL_REFERENCE_RATE) ))

    return int(f_number), int(block)


def midi_note_to_frequency(midi_note: int, a4: float = 440.0) -> float:
    """
    Convert a MIDI note number to frequency in Hz.

    MIDI note 69 is A4 (440 Hz).
    """
    return a4 * (2 ** ((max(0, min(127, midi_note)) - 69) / 12.0))


def midi_note_to_f_number_and_block(midi_note: int, a4: float = 440.0) -> tuple[int, int]:
    """
    Convert a MIDI note number to an OPL F-number and block.

    MIDI note 69 is A4 (440 Hz).
    """
    frequency = midi_note_to_frequency(midi_note, a4=a4)
    return frequency_to_f_number_and_block(frequency)
