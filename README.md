# Python OPL3 library

Low-level wrapper around [Nuked OPL3](https://github.com/nukeykt/Nuked-OPL3) C implementation
and higher-level utilities to make programming the OPL3 chip fun. 

## Quickstart

OPL3 is a complicated beast. The `OPL3State`, `Channel` and `Operator` classes 
are supposed to make it easy to get some sounds out of it.

```python
import time
from pyopl import *

# low-level wrapper
chip = OPL3Chip(48000)

# program the chip 'by hand' ...
chip.write(0xA0, 0x20)

# schedule writes into the future
# (in this case: execute at exactly one second of rendered audio)
chip.write(0xA0, 0x20, sample=48000)

# use high-level helper
state = OPL3State(chip)

# all channel-wide settings can be set with the Channel class
state.write_channel(0, Channel(fm=True, feedback=3))

# Configure two operators for channel 0
# operator settings are stored in Operator classes
state.write_operators(
  0,
  Operator(freq_multiplier=2, waveform=2, decay=1),
  Operator(decay=5, release=2, vibrato=True, tremolo=True)
)

# Small wrapper around the sounddevice library to generate
# the audio stream in the background
with AudioStream(chip):
    # play a note on channel 0
    state.midi_note_on(0, 48)
    # let it sing a little
    time.sleep(1.)
    # clear the note-on bit
    state.note_off(0)
    # and let the release envelope do it's thing
    time.sleep(.5)
```

## [Examples](examples/)

- [example_play.py](examples/example_play.py): Play two-operator notes on 18 channels.
- [example_beat.py](examples/example_beat.py): Use the OPL3 rhythm mode and schedule register writes into the future, for accurate timing. 
- [example_multichip.py](examples/example_multichip.py): Use two OPL3Chip instances at the same time to play 36 voices simultaneously.
- [sound_editor.py](examples/sound_editor.py): Interactively edit all parameters of a single melody channel in 2-op or 4-op mode. Very useful to get to know the OPL3 capabilities.
- [beat_tracker/](examples/beat_tracker/): A little console tracker for OPL3 rhythms. Allows live editing of patterns and all relevant settings.
  Run with `python examples/beat_tracker`.


## Development

```shell
# create venv and install `build` tool
python -m venv env
source env/bin/activate
pip install -U build

# render src/pyopl/_opl3.c with doc-strings from _opl3.pyi file
python tools/add_doc_strings.py
# build the package
python -m build
# install package into venv
pip install --force-reinstall dist/*.whl
# run the unit-tests
python -m unittest discover tests/
```

The `src/pyopl/_opl3.pyi` file is the source of truth for all `OPL3Chip` annotations and doc-strings.
They are copied to the c-implementation before building so source code, your IDE 
and Python's `help(OPL3Chip)` all show the same.


## Resources

Stuff i found useful to understand the OPL3 logic and create the high-level helper classes:

- https://www.asvcorp.ru/darch/docs/sound/opl3/index.html
  This is **the main document** out there. What would we do without it??
- https://gist.github.com/alexxior/4ab75ac60bc248634feaf1afba63b129/79ae6d626abcb21578b5df8b93ee4385c50f3131
- https://oplx.com/opl3/docs/ymf262.pdf
- https://www.opl3.com/wp-content/uploads/2019/08/amsc-Programmers-Guide.pdf
- https://forums.submarine.org.uk/phpBB/viewforum.php?f=9
