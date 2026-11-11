"""

| inst | op    | channel | ADSR | waveform  | feedback | fm  |
+------+-------+---------+------+-----------+----------+-----+
| BD   | 12+15 |       6 |  yes |       yes |      yes | yes |
| SD   |    16 |       7 |  yes |       yes |       no |  no |
| TT   |    14 |       8 |  yes |       yes |       no |  no |
| CY   |    17 | 6, 7, 8 |  yes |      *yes |       no |  no |
| HH   |    13 | 6, 7, 8 |  yes |      *yes |       no |  no |
"""
import textwrap
import time

from pyopl import *

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

    state.set_rhythm_mode(True)

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
        state.write_channel(ch, Channel(fm=ch == 6, feedback=5))
        state.midi_note_on(ch, 40 if ch == 6 else 52, note_on=False)

    # BD SD TT CY HH
    pattern = [line.strip() for line in textwrap.dedent(PATTERN2).splitlines() if line.strip()]

    sample = 0
    for i in range(2):
        for line in pattern:
            note_on = [c != "." for c in line[:5]]

            state.rhythm_on(sample=sample)
            state.rhythm_on(*note_on, sample=sample + 1)
            sample += int(.1 * SR)

    with AudioStream(chip):
        time.sleep(sample / SR + .5)


if __name__ == "__main__":
    main()
