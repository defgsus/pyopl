"""
Plays 36 simultaneous 2-op tones at once, using two chips
"""
import time

from pyopl import *


def main():
    SR = 48000

    # create two chips
    chips = [
        OPL3Chip(SR)
        for _ in range(2)
    ]
    # and a state object for each
    states = [OPL3State(chip) for chip in chips]

    note = 30
    note_index = 0
    # advance in a nice minor interval
    scale_intervals = [3, 4, 3, 2]
    for state in states:
        # 18 channels on each chip
        for ch in range(18):
            state.write_channel(ch, Channel())
            # don't use full output-level for the carrier operator
            # because we are mixing quite a lot of channels
            state.write_operators(ch, Operator(), Operator(output_level=50))
            # start each note 100ms apart
            state.midi_note_on(ch, note, sample=int(note_index * .1 * SR))
            # advance in note scale
            note += scale_intervals[note_index % len(scale_intervals)]
            note_index += 1

    # AudioStream supports 1 or more chips
    with AudioStream(*chips):
        # let it progress
        time.sleep(5)

        # stop all notes
        for state in states:
            for ch in range(18):
                state.note_off(ch)

        time.sleep(1)


if __name__ == "__main__":
    main()
