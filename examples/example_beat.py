"""
Example how to use the OPL3's rhythm mode
and how to schedule register writes into the future.

OPL3 specifics are quite complicated. Especially the rhythm instruments have
specific operators and channels on which they are configured.
This table shows them for each instrument:

| inst | op    | channel | ADSR | waveform  | feedback | fm  |
+------+-------+---------+------+-----------+----------+-----+
| BD   | 12+15 |       6 |  yes |       yes |      yes | yes |
| SD   |    16 |       7 |  yes |       yes |       no |  no |
| TT   |    14 |       8 |  yes |       yes |       no |  no |
| CY   |    17 | 6, 7, 8 |  yes |      *yes |       no |  no |
| HH   |    13 | 6, 7, 8 |  yes |      *yes |       no |  no |

ADSR (attack, decay, sustain, release envelope) and waveform are Operator settings.
feedback and frequency-modulation are channel settings.
The basedrum has two operators and is the only rhythm instruments that supports feedback and fm.
The pitch of the instruments is set per channel, BUT, only the basedrum has it's own pitch.
Snare, Tom, Cymbal and Highhat all share the pitches in complicated ways.
E.g. you can not change the pitch of the Snare without also affecting
the pitch of Cymbal and Highhat in some way.
"""
import textwrap
import time

from pyopl import *

# BD SD TT CY HH
PATTERN1 = """
x..xx ---
.....
x...x 
.....
.x..x 
.....
....x 
..x..
x...x ---
.....
x...x 
x....
.x..x 
.....
..x.x 
.....
"""

PATTERN2 = """
x..xx ---
x....
....x 
.....
.x..x 
.....
x...x 
.....
....x ---
.....
.xx.x 
.....
....x 
..x..
x.x.x 
..x..
"""

def main():
    SR = 48000

    chip = OPL3Chip(SR)
    state = OPL3State(chip)

    # Not really necessary, because state.rhythm_on(...) will also set it later
    state.set_rhythm_mode(True)

    # Create one Operator class and reuse it for all instruments
    # BD
    op = Operator(decay=4, waveform=0, freq_multiplier=0)
    op.write(chip, 12)
    op.write(chip, 15)
    # SD
    op.freq_multiplier = 1
    op.output_level = 50
    op.decay = 5
    op.write(chip, 16)
    # TT
    op.decay = 4
    op.write(chip, 14)
    # CY
    op.decay = 1
    op.write(chip, 17)
    # HH
    op.decay = 8
    op.output_level = 63
    op.write(chip, 13)

    # 6 = BD + HH
    # 7 = SD + CY + HH
    # 8 = TT + CY + HH
    for ch in range(6, 9):
        # fm and feedback channel settings are only used on channel 6 (basedrum)
        state.write_channel(ch, Channel(fm=True, feedback=5))
        # Set the frequency of the channel, but do not set note_on-bit, or it won't work
        state.midi_note_on(ch, 40 if ch == 6 else 52, note_on=False)

    pattern = [line.strip() for line in textwrap.dedent(PATTERN2).splitlines() if line.strip()]

    # now instead of calling the drums in real-time we schedule the
    # note-on register writes at absolute sample positions
    sample = 0
    for i in range(2):
        for line in pattern:
            note_on = [c != "." for c in line[:5]]

            # clear all note_on-bits for the percussion instruments
            state.rhythm_on(sample=sample)
            # set the note_on-bits for the instruments per pattern-row
            state.rhythm_on(*note_on, sample=sample + 1)
            # advance sample position
            sample += int(.1 * SR)

    with AudioStream(chip):
        # wait until all scheduled register writes have happend + half a second
        time.sleep(sample / SR + .5)


if __name__ == "__main__":
    main()
