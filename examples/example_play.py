"""
Play a tone on each of the 18 available OPL3 channels
"""
import time

from pyopl import *


def main():
    SR = 48000

    chip = OPL3Chip(SR)
    state = OPL3State(chip)

    state.set_4_ops()
    state.set_rythm_mode(False)

    operators = [
        Operator(
            decay=3,
            freq_multiplier=2,
            waveform=i,
        )
        for i in range(8)
    ]
    for ch in range(18):
        state.write_channel(ch, Channel(feedback=ch%8))
        op = operators[ch % len(operators)]
        state.write_operators(ch, op, op)

    with AudioStream(chip):
        for ch in range(18):
            print(f"channel {ch}")
            state.midi_note_on(ch, 48+ch)
            time.sleep(.1)
            state.note_off(ch)
            time.sleep(.3)



if __name__ == "__main__":
    main()
