"""
Play a tone on each of the 18 available OPL3 channels in 2-operator mode.
"""
import time

from pyopl import *


def main():
    SR = 48000

    chip = OPL3Chip(SR)
    state = OPL3State(chip)

    # Create 8 operator configurations, each with a different waveform
    operators = [
        Operator(
            decay=5,
            release=3,
            freq_multiplier=2,
            waveform=i,
        )
        for i in range(8)
    ]
    for ch in range(18):
        # Set channel attributes
        # especially routing to left and right output (default parameters of Channel)
        state.write_channel(ch, Channel(feedback=ch%8))
        # pick one of the operator configs for this channel
        op = operators[ch % len(operators)]
        # and apply them to the channel
        # each channel uses two operators for the voice
        state.write_operators(ch, op, op)

    with AudioStream(chip):
        # play a tone on each of the channels
        for ch in range(18):
            print(f"channel {ch}")
            state.midi_note_on(ch, 48+ch)
            # the AudioStream object process the chip in the background
            # so we can sleep a little to let the notes play
            time.sleep(.1)
            # Turn the note off
            # Internally the state object has remembered the last played note on this channel
            # so it can write the same frequency to the register but without the note_on-bit
            state.note_off(ch)
            time.sleep(.3)

        time.sleep(2)

    # In the old MS-DOS days, it was bad practice to leave the note-on bits set at the
    # end of the program, but this is just an emulator. Audio is already off at this point,
    # regardless of what the chip was doing.

if __name__ == "__main__":
    main()
