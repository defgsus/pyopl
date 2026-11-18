import random
import pprint
import time

from pyopl import *
from examples.tracker.data import *
from examples.tracker.audio import *


def create_song():
    song = Song(config=SongConfig(
        channels=[
            ChannelConfig(polyphony=8),
            ChannelConfig(polyphony=8, type="4OP"),
            ChannelConfig(polyphony=1, type="PERC"),
            ChannelConfig(polyphony=1, type="PERC"),
        ]
    ))

    song.instruments[0] = Instrument(
        name="Synth2",
        type="2OP",
        channel_settings=(
            Channel(fm=True, feedback=3),
            Channel(),
        ),
        operators=(
            Operator(output_level=0, decay=4, release=10),
            Operator(attack=15, decay=5, release=4, freq_multiplier=4),
            Operator(),
            Operator(),
        )
    )
    song.instruments[1] = Instrument(
        name="Synth4",
        type="4OP",
        channel_settings=(
            Channel(fm=True, feedback=3),
            Channel(),
        ),
        operators=(
            Operator(freq_multiplier=4, output_level=35),
            Operator(attack=10),
            Operator(),
            Operator(),
        )
    )

    for i, name, type in (
            (0, "Basefrum", "BD"),
            (1, "Snare", "SD"),
            (2, "Tom", "TT"),
            (3, "Cymbal", "CY"),
            (4, "HiHat", "HH"),
    ):
        song.instruments[i + 2] = Instrument(
            name=name,
            type=type,
            channel_settings=(Channel(fm=True), Channel()),
            operators=(
                Operator(decay=8, release=5, output_level=40 if i >= 3 else 63),
                Operator(decay=7),
                Operator(), Operator(),
            )
        )

    rng = random.Random(23)

    pattern = song.patterns[0]
    pattern[0, 0].instrument = 0
    pattern[1, 0].instrument = 1
    for row in range(pattern.length):
        if row % 2 == 0:
            pattern[0, row].note = rng.randint(32, 64)
        if row % 8 == 0:
            pattern[1, row].note = rng.randint(32, 64)
            pattern[1, row].volume = rng.randint(20, 40)

        if row % 8 in (0, 1, 3):
            pattern[2, row].note = rng.randint(32, 64)
            pattern[2, row].instrument = 2
        if row % 8 in (4, ):
            pattern[2, row].note = rng.randint(32, 64)
            pattern[2, row].instrument = 3
        if row % 2 in (0, ):
            pattern[3, row].note = 48
            pattern[3, row].instrument = 5
        if row % 2 in (1, ):
            pattern[3, row].note = 48
            pattern[3, row].instrument = 6


    return song


def main():
    SR = 48000
    song = create_song()
    player = Player(song, SR)
    #pool = OPL3Pool(SR, song, debug=True)
    print("channels:")
    pprint.pp(player.pool.channels)

    if 0:
        sample = 0
        pattern = song.patterns[0]
        for row in range(pattern.length):
            for ch in range(song.num_channels):
                cell = pattern[ch, row]
                pool.program_cell(ch, cell, sample)
            sample += int(SR * 0.1)

    player.start_audio()
    try:
        player.play()
        while True:
            time.sleep(1)
            if player.current_song_row >= 256:
                break
    except KeyboardInterrupt:
        pass
    finally:
        player.stop_audio()


if __name__ == "__main__":
    main()

