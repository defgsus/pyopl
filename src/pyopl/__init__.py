try:
    from ._opl3 import OPL3Chip
except ImportError:
    pass

from .util import (
    frequency_to_f_number_and_block,
    midi_note_to_frequency,
    midi_note_to_f_number_and_block,
)
from .state import (
    CHANNEL_REGISTERS,
    OP_REGISTERS,
    OPL2_OP_INDICES,
    OPL3_OP_INDICES,
    Waveform,
    Channel,
    Operator,
    OPL3State,
)
from .stream import AudioStream


# The Chip's internal sample rate
DEFAULT_SAMPLE_RATE = 49716
